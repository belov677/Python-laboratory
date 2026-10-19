// Загрузка каталога склада и отображение товаров ниже минимального остатка
async function loadLowStock() {
  const response = await fetch("/items/low-stock");
  const items = await response.json();
  document.querySelector("#low").innerHTML = items
    .map(i => `<div class="item below-min">${i.sku} ${i.name}: ${i.quantity}/${i.min_stock}</div>`)
    .join("");
}
loadLowStock();
