import test from "node:test";
import assert from "node:assert/strict";
import { keyboardCell } from "../src/board-keyboard";

test("visual board keyboard movement stays inside rows and bounds", () => {
  for (const [index, key, expected] of [[0, "ArrowLeft", 0], [2, "ArrowRight", 2], [0, "ArrowUp", 0], [8, "ArrowDown", 8], [4, "ArrowLeft", 3], [4, "ArrowRight", 5], [4, "ArrowUp", 1], [4, "ArrowDown", 7], [4, "Home", 3], [4, "End", 5]] as const)
    assert.equal(keyboardCell(index, key, 3, 9), expected);
  assert.equal(keyboardCell(6, "End", 3, 8), 7);
});
test("keyboard navigation leaves activation keys and invalid bounds alone", () => {
  assert.equal(keyboardCell(0, "Enter", 3, 9), null);
  for (const [index, cols, count] of [[-1, 3, 9], [9, 3, 9], [0, 0, 9], [0, 3, 0], [0.5, 3, 9]])
    assert.equal(keyboardCell(index, "ArrowRight", cols, count), null);
});
