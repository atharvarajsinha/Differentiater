function total(items, taxRate = 0) {
  let sum = 0;
  for (const item of items) {
    sum += item.price * item.quantity;
  }
  return sum * (1 + taxRate);
}
