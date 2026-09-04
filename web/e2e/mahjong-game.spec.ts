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

/** Same as createMahjongRoom, but sets a nonzero zimo bonus and KLPPDD
 * amount on the rules form first, to exercise both optional bonuses. */
async function createMahjongRoomWithBonuses(page: Page) {
  await page.getByTestId("new-room-btn").click();
  await expect(page).toHaveURL(/\/new/);
  await page.getByTestId("game-tile-mahjong").click();
  await page.getByTestId("rule-zimo-bonus").fill("5");
  await page.getByTestId("rule-klppdd").fill("10");
  await page.getByTestId("create-room-btn").click();
  await expect(page).toHaveURL(/\/room\//);
}

function amountFor(page: Page, name: string) {
  return page
    .locator(`[data-testid="standing-row"][data-player^="${name}"] [data-testid="standing-amount"]`)
    .first();
}

test("the 5/1 半 preset fills in its stakes table", async ({ page }) => {
  await login(page, `Preset-${Date.now().toString(36)}`);
  await page.getByTestId("new-room-btn").click();
  await page.getByTestId("game-tile-mahjong").click();

  await page.getByTestId("mahjong-preset-5/1-半").click();

  await expect(page.getByTestId("rule-base")).toHaveValue("500");
  await expect(page.getByTestId("rule-yao")).toHaveValue("3");
  await expect(page.getByTestId("rule-gang")).toHaveValue("3");
  await expect(page.getByTestId("rule-zimo-bonus")).toHaveValue("5");
  await expect(page.getByTestId("rule-klppdd")).toHaveValue("5");
  await expect(page.getByTestId("rule-tai-1-hu")).toHaveValue("4");
  await expect(page.getByTestId("rule-tai-1-zimo")).toHaveValue("2");
  await expect(page.getByTestId("rule-tai-7-hu")).toHaveValue("256");
  await expect(page.getByTestId("rule-tai-7-zimo")).toHaveValue("128");
  await expect(page.getByTestId("tai-row-add")).toBeVisible();
});

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
      await expect(p.getByTestId("dealer-seat")).toHaveAttribute("data-wind", "1");
    }

    // Alice YAOs herself (咬自己): each of the other 3 pays 2 chips. Displayed
    // amounts are chip stacks (base 300 + net), not raw dollars.
    await alice.getByTestId("yao-btn").click();
    await alice.getByTestId("pick-seat-0").click();
    await alice.getByTestId("yao-ming-btn").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(amountFor(p, "Alice")).toHaveText("306", { timeout: 10_000 }); // 300 + 3*2
    }

    // Bob declares ANGANG: each of the other 3 pays gang_chips*2=4. Bob
    // already paid 2 into Alice's YAO, so his net is -2+12=10.
    await bob.getByTestId("gang-btn").click();
    await bob.getByTestId("pick-angang").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(amountFor(p, "Bob")).toHaveText("310", { timeout: 10_000 }); // 300 - 2 + 3*4
    }

    // Dan directly HUs off Cara (seat 2) at 2 tai — closes the hand. Dan
    // (seat 3) isn't the dealer (seat 0), so the dealer rotates for hand 2
    // regardless of the earlier gang.
    await dan.getByTestId("hu-btn").click();
    await dan.getByTestId("pick-seat-2").click();
    await dan.getByTestId("tai-plus").click();
    await dan.getByTestId("confirm-hu-btn").click();

    for (const p of [alice, bob, cara, dan]) {
      await expect(p.getByTestId("dealer-seat")).toHaveAttribute("data-wind", "1", {
        timeout: 10_000,
      });
      // Back to the action buttons for hand 2 on every device.
      await expect(p.getByTestId("yao-btn")).toBeVisible({ timeout: 10_000 });
    }
    // Dealer started at seat 0 (東, Alice); Dan (seat 3) winning rotates it
    // to seat 1 (南, Bob).
    await expect(alice.getByTestId("dealer-seat")).toHaveAttribute("data-dealer-seat", "1");
    await expect(
      alice.locator('[data-testid="standing-row"][data-player^="Bob"]'),
    ).toHaveAttribute("data-dealer", "true");

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

test("zimo bonus and KLPPDD toggles add on top of the tai payout", async ({ browser }) => {
  const contexts = await Promise.all([0, 1, 2, 3].map(() => browser.newContext()));
  const [alice, bob, cara, dan] = await Promise.all(contexts.map((c) => c.newPage()));

  try {
    const uniq = Date.now().toString(36);
    await login(alice, `Alice-${uniq}`);
    await login(bob, `Bob-${uniq}`);
    await login(cara, `Cara-${uniq}`);
    await login(dan, `Dan-${uniq}`);

    await createMahjongRoomWithBonuses(alice);
    const inviteCode = (await alice.getByTestId("invite-code").textContent())?.trim();

    for (const p of [bob, cara, dan]) {
      await p.getByTestId("room-code-input").fill(inviteCode!);
      await p.getByTestId("join-room-btn").click();
      await expect(p).toHaveURL(/\/room\//);
    }
    for (const p of [alice, bob, cara, dan]) {
      await expect(p.getByTestId("lobby-member")).toHaveCount(4, { timeout: 10_000 });
    }

    await alice.getByTestId("start-game-btn").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(p.getByTestId("yao-btn")).toBeVisible({ timeout: 10_000 });
    }

    // Alice self-draws at 1 tai (default table: hu=4/zimo=4) with the zimo
    // bonus (5) and KLPPDD (10) both on: each of the other 3 pays
    // 4 + 5 + 10 = 19.
    await alice.getByTestId("hu-btn").click();
    await alice.getByTestId("pick-seat-0").click();
    await alice.getByTestId("zimo-bonus-toggle").click();
    await alice.getByTestId("klppdd-toggle").click();
    await alice.getByTestId("confirm-hu-btn").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(amountFor(p, "Alice")).toHaveText("357", { timeout: 10_000 }); // 300 + 3*19
      await expect(amountFor(p, "Bob")).toHaveText("281", { timeout: 10_000 }); // 300 - 19
    }

    // Bob directly HUs off Cara (seat 2) at 1 tai with KLPPDD on (no zimo
    // bonus option for a direct win): Cara alone pays 4 + 3*10 = 34.
    await bob.getByTestId("hu-btn").click();
    await bob.getByTestId("pick-seat-2").click();
    await expect(bob.getByTestId("zimo-bonus-toggle")).toHaveCount(0);
    await bob.getByTestId("klppdd-toggle").click();
    await bob.getByTestId("confirm-hu-btn").click();
    for (const p of [alice, bob, cara, dan]) {
      await expect(amountFor(p, "Bob")).toHaveText("315", { timeout: 10_000 }); // 281 + 34
      await expect(amountFor(p, "Cara")).toHaveText("247", { timeout: 10_000 }); // 281 - 34
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
