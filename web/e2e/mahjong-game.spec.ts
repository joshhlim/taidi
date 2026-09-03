import { test, expect, type Page } from "@playwright/test";

/**
 * Drives a Mahjong game across four separate browser contexts, mirroring
 * full-game.spec.ts's convergence-testing pattern for Taidi.
 */

async function login(page: Page, name: string) {
  await page.goto("/");
  await page.getByTestId("display-name-input").fill(name);
  await page.getByTestId("continue-btn").click();
  await expect(page.getByText(`Signed in as ${name}`)).toBeVisible();
}

async function createMahjongRoom(page: Page) {
  await page.getByTestId("new-room-btn").click();
  await expect(page).toHaveURL(/\/new/);
  await page.getByTestId("game-tile-mahjong").click();
  await page.getByTestId("create-room-btn").click();
  await expect(page).toHaveURL(/\/room\//);
}

function amountFor(page: Page, name: string) {
  return page
    .locator(`[data-testid="standing-row"][data-player^="${name}"] [data-testid="standing-amount"]`)
    .first();
}

test("a full hand across four simulated devices", async ({ browser }) => {
  const contexts = await Promise.all([0, 1, 2, 3].map(() => browser.newContext()));
  const [alice, bob, cara, dan] = await Promise.all(contexts.map((c) => c.newPage()));

  try {
    const uniq = Date.now().toString(36);
    await login(alice, `Alice-${uniq}`);
    await login(bob, `Bob-${uniq}`);
    await login(cara, `Cara-${uniq}`);
    await login(dan, `Dan-${uniq}`);

    await createMahjongRoom(alice);
    const inviteCode = (await alice.getByTestId("invite-code").textContent())?.trim();
    expect(inviteCode).toMatch(/^[A-Z0-9]{6}$/);

    for (const p of [bob, cara, dan]) {
      await p.getByTestId("room-code-input").fill(inviteCode!);
      await p.getByTestId("join-room-btn").click();
      await expect(p).toHaveURL(/\/room\//);
    }

    for (const p of [alice, bob, cara, dan]) {
      await expect(p.getByTestId("lobby-member")).toHaveCount(4, { timeout: 10_000 });
    }

    // Host starts; everyone transitions to the live table with the wind/dealer
    // indicator and the three action buttons.
    await alice.getByTestId("start-game-btn").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(p.getByTestId("yao-btn")).toBeVisible({ timeout: 10_000 });
      await expect(p.getByTestId("wind-dealer")).toContainText("Wind 1");
    }

    // Alice YAOs herself (咬自己): each of the other 3 pays.
    await alice.getByTestId("yao-btn").click();
    await alice.getByTestId("pick-seat-0").click();
    await alice.getByTestId("yao-ming-btn").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(amountFor(p, "Alice")).toHaveText("$3.00", { timeout: 10_000 });
    }

    // Bob declares ANGANG: each of the other 3 pays double, and the hand is
    // now flagged as having had a gang (visible via dealer rotation later).
    await bob.getByTestId("gang-btn").click();
    await bob.getByTestId("pick-angang").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(amountFor(p, "Bob")).toHaveText("$5.00", { timeout: 10_000 });
    }

    // Dan directly HUs off Cara (seat 2) at 2 tai — closes the hand. A gang
    // happened this hand, so the dealer should rotate for hand 2.
    await dan.getByTestId("hu-btn").click();
    await dan.getByTestId("pick-seat-2").click();
    await dan.getByTestId("tai-plus").click();
    await dan.getByTestId("confirm-hu-btn").click();

    for (const p of [alice, bob, cara, dan]) {
      await expect(p.getByTestId("wind-dealer")).toContainText("Wind 1", { timeout: 10_000 });
      // Back to the action buttons for hand 2 on every device.
      await expect(p.getByTestId("yao-btn")).toBeVisible({ timeout: 10_000 });
    }
    // Dealer started at seat 0 (東, Alice); a gang rotates it to seat 1 (南, Bob).
    await expect(alice.getByTestId("wind-dealer")).toContainText("Bob");

    // Host ends the game — everyone sees the final-stats screen.
    await alice.getByTestId("end-game-btn").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(p.getByTestId("game-over")).toBeVisible({ timeout: 10_000 });
      await expect(p.getByTestId("standing-row")).toHaveCount(4);
    }
  } finally {
    await Promise.all(contexts.map((c) => c.close()));
  }
});

test("a member can leave a mahjong lobby, and the host can disband it", async ({ browser }) => {
  const aliceCtx = await browser.newContext();
  const bobCtx = await browser.newContext();
  const alice = await aliceCtx.newPage();
  const bob = await bobCtx.newPage();

  try {
    const uniq = Date.now().toString(36);
    await login(alice, `Alice-${uniq}`);
    await login(bob, `Bob-${uniq}`);

    await createMahjongRoom(alice);
    const inviteCode = (await alice.getByTestId("invite-code").textContent())?.trim();

    await bob.getByTestId("room-code-input").fill(inviteCode!);
    await bob.getByTestId("join-room-btn").click();
    await expect(bob).toHaveURL(/\/room\//);
    await expect(alice.getByTestId("lobby-member")).toHaveCount(2, { timeout: 10_000 });

    await bob.getByTestId("leave-room-btn").click();
    await expect(bob).toHaveURL("/");
    await expect(alice.getByTestId("lobby-member")).toHaveCount(1, { timeout: 10_000 });

    await alice.getByTestId("disband-room-btn").click();
    await expect(alice).toHaveURL("/");
  } finally {
    await aliceCtx.close();
    await bobCtx.close();
  }
});
