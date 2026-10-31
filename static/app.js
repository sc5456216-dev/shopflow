let token = localStorage.getItem("access");
const $ = (id) => document.getElementById(id);
const money = (value) => `Rs ${Number(value).toFixed(2)}`;
let currentView = "shop";

function say(text) {
  $("message").textContent = text || "";
}

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

async function request(path, options = {}, auth = true) {
  const headers = { "Content-Type": "application/json" };
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`/api${path}`, { ...options, headers });
  if (res.status === 401 && auth && token) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }
  if (res.status === 401) throw new Error("Please log in first.");
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(Object.values(data).flat().join(" ") || "Request failed");
  }
  return res.status === 204 ? null : res.json();
}

function showView(name) {
  currentView = name;
  say("");
  for (const view of ["shop", "cart", "orders", "auth"]) {
    $(`view-${view}`).hidden = view !== name;
  }
  document.querySelectorAll("button.nav[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === name);
  });
  if (name === "cart") loadCart().catch((e) => say(e.message));
  if (name === "orders") loadOrders().catch((e) => say(e.message));
}

function requireLogin(name) {
  if (token) return showView(name);
  showView("auth");
  say("Please log in to continue.");
}

function logout() {
  token = null;
  localStorage.removeItem("access");
  $("auth-button").textContent = "Log in";
  $("cart-count").textContent = "0";
  showView("shop");
}

async function login(username, password) {
  const data = await request("/token/", { method: "POST", body: JSON.stringify({ username, password }) }, false);
  token = data.access;
  localStorage.setItem("access", token);
  $("auth-button").textContent = "Log out";
  showView("shop");
  await updateCartCount();
}

async function updateCartCount() {
  if (!token) return;
  const items = await request("/cart/");
  $("cart-count").textContent = items.reduce((sum, item) => sum + item.quantity, 0);
}

function productCard(product) {
  const card = el("div", undefined, "card");
  card.append(el("div", product.name.charAt(0), "thumb"));
  card.append(el("strong", product.name));
  card.append(el("div", product.category_name || "Uncategorized", "muted"));
  card.append(el("div", product.description, "muted"));
  card.append(el("div", money(product.price), "price"));
  card.append(el("div", product.stock > 0 ? `${product.stock} in stock` : "Out of stock", "muted"));
  const add = el("button", "Add to cart");
  add.disabled = product.stock === 0;
  add.addEventListener("click", async () => {
    if (!token) return requireLogin("shop");
    try {
      await request("/cart/", { method: "POST", body: JSON.stringify({ product_id: product.id, quantity: 1 }) });
      await updateCartCount();
      say("");
    } catch (error) {
      say(error.message);
    }
  });
  card.append(add);
  return card;
}

async function loadProducts() {
  const params = new URLSearchParams();
  if ($("search").value) params.set("search", $("search").value);
  if ($("category").value) params.set("category", $("category").value);
  const products = await request(`/products/?${params}`, {}, false);
  $("products").replaceChildren(...products.map(productCard));
  if (!products.length) $("products").append(el("p", "No products found.", "muted"));
}

async function loadCategories() {
  const categories = await request("/categories/", {}, false);
  $("category").append(...categories.map((c) => new Option(c.name, c.id)));
}

function cartRow(item) {
  const li = el("li");
  const top = el("div", undefined, "row");
  top.append(el("strong", item.product.name), el("span", money(item.subtotal)));
  const controls = el("div", undefined, "row");
  const qty = el("input");
  qty.type = "number";
  qty.min = "1";
  qty.max = String(item.product.stock);
  qty.value = item.quantity;
  qty.setAttribute("aria-label", "Quantity");
  qty.addEventListener("change", async () => {
    try {
      await request(`/cart/${item.id}/`, { method: "PATCH", body: JSON.stringify({ quantity: Number(qty.value) }) });
    } catch (error) {
      say(error.message);
    }
    loadCart();
  });
  const remove = el("button", "Remove", "secondary");
  remove.addEventListener("click", async () => {
    await request(`/cart/${item.id}/`, { method: "DELETE" }).catch((e) => say(e.message));
    loadCart();
  });
  controls.append(qty, remove);
  li.append(top, controls);
  return li;
}

async function loadCart() {
  const items = await request("/cart/");
  const total = items.reduce((sum, item) => sum + Number(item.subtotal), 0);
  $("cart-list").replaceChildren(...items.map(cartRow));
  if (!items.length) $("cart-list").append(el("p", "Your cart is empty.", "muted"));
  $("cart-total").textContent = money(total);
  $("cart-count").textContent = items.reduce((sum, item) => sum + item.quantity, 0);
}

function orderRow(order) {
  const li = el("li");
  const top = el("div", undefined, "row");
  top.append(el("strong", `Order #${order.id}`), el("span", order.status, "badge"));
  li.append(top);
  for (const item of order.items) {
    li.append(el("div", `${item.quantity} x ${item.product_name} (${money(item.unit_price)})`, "muted"));
  }
  li.append(el("div", `Total: ${money(order.total)}`, "price"));
  li.append(el("div", `Ship to: ${order.shipping_address}`, "muted"));
  if (order.status === "pending") {
    const row = el("div", undefined, "row");
    const pay = el("button", "Pay (demo)");
    const cancel = el("button", "Cancel order", "secondary");
    pay.addEventListener("click", () => orderAction(order.id, "pay"));
    cancel.addEventListener("click", () => orderAction(order.id, "cancel"));
    row.append(pay, cancel);
    li.append(row);
  }
  return li;
}

async function orderAction(id, action) {
  try {
    await request(`/orders/${id}/${action}/`, { method: "POST" });
    await loadOrders();
    await loadProducts();
  } catch (error) {
    say(error.message);
  }
}

async function loadOrders() {
  const orders = await request("/orders/");
  $("order-list").replaceChildren(...orders.map(orderRow));
  if (!orders.length) $("order-list").append(el("p", "No orders yet.", "muted"));
}

document.querySelectorAll("button.nav[data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.view === "shop") return showView("shop");
    requireLogin(button.dataset.view);
  });
});

$("auth-button").addEventListener("click", () => (token ? logout() : showView("auth")));
$("search").addEventListener("input", () => loadProducts().catch((e) => say(e.message)));
$("category").addEventListener("change", () => loadProducts().catch((e) => say(e.message)));

$("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  say("");
  const username = $("username").value;
  const password = $("password").value;
  try {
    if (event.submitter.dataset.mode === "register") {
      await request("/register/", { method: "POST", body: JSON.stringify({ username, password }) }, false);
    }
    await login(username, password);
  } catch (error) {
    say(error.message);
  }
});

$("checkout-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await request("/checkout/", { method: "POST", body: JSON.stringify({ shipping_address: $("address").value }) });
    event.target.reset();
    await loadProducts();
    showView("orders");
    await updateCartCount();
  } catch (error) {
    say(error.message);
  }
});

(async function init() {
  if (token) $("auth-button").textContent = "Log out";
  showView("shop");
  await Promise.all([loadCategories(), loadProducts()]).catch((e) => say(e.message));
  await updateCartCount().catch(() => {});
})();
