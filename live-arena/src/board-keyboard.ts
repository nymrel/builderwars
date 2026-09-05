/** Move within the visual board order without wrapping across row edges. */
export function keyboardCell(index: number, key: string, cols: number, count: number): number | null {
  if (![index, cols, count].every(Number.isInteger) || cols < 1 || count < 1 || index < 0 || index >= count) return null;
  switch (key) {
    case "ArrowLeft": return index % cols ? index - 1 : index;
    case "ArrowRight": return index % cols < cols - 1 && index + 1 < count ? index + 1 : index;
    case "ArrowUp": return index >= cols ? index - cols : index;
    case "ArrowDown": return index + cols < count ? index + cols : index;
    case "Home": return index - index % cols;
    case "End": return Math.min(index - index % cols + cols - 1, count - 1);
    default: return null;
  }
}
