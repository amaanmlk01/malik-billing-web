function createItemRow() {
    const row = document.createElement("div");
    row.className = "item-row";

    row.innerHTML = `
        <input type="text" class="item-name" placeholder="Item">
        <input type="number" class="item-qty" placeholder="Qty" min="0">
        <input type="number" class="item-rate" placeholder="Rate" min="0">
        <input type="text" class="item-amount" placeholder="Amount" readonly>
    `;

    // attach events immediately
    row.querySelector(".item-qty").addEventListener("input", calculateTotals);
    row.querySelector(".item-rate").addEventListener("input", calculateTotals);

    return row;
}

function addItem() {
    const container = document.getElementById("items");
    const row = createItemRow();
    container.appendChild(row);
}

function calculateTotals() {
    const rows = document.querySelectorAll(".item-row");
    let subtotal = 0;

    rows.forEach((row) => {
        const qty = parseFloat(row.querySelector(".item-qty").value) || 0;
        const rate = parseFloat(row.querySelector(".item-rate").value) || 0;
        const amount = qty * rate;

        row.querySelector(".item-amount").value = amount.toFixed(2);
        subtotal += amount;
    });

    const received = parseFloat(document.getElementById("receivedAmount").value) || 0;
    const balance = subtotal - received;

    document.getElementById("subtotal").value = subtotal.toFixed(2);
    document.getElementById("balanceDue").value = balance.toFixed(2);
}

// 🔥 CRITICAL FIX — initialize events properly
document.addEventListener("DOMContentLoaded", () => {

    // attach event to FIRST row
    document.querySelectorAll(".item-qty, .item-rate").forEach(input => {
        input.addEventListener("input", calculateTotals);
    });

    document.getElementById("receivedAmount")
        .addEventListener("input", calculateTotals);

    // attach button event safely
    const generateBtn = document.querySelector(".generate-btn");
    if (generateBtn) {
        generateBtn.addEventListener("click", generateInvoice);
    }

loadCustomers();

    const customerSelect = document.getElementById("customerSelect");
    if (customerSelect) {
        customerSelect.addEventListener("change", autofillCustomer);
    }
});

function generateInvoice() {
    const items = [];

    document.querySelectorAll(".item-row").forEach(row => {
        const name = row.querySelector(".item-name").value;
        const qty = row.querySelector(".item-qty").value;
        const rate = row.querySelector(".item-rate").value;
        const amount = row.querySelector(".item-amount").value;

        if (name) {
            items.push({ name, qty, rate, amount });
        }
    });

    const data = {
        billTo: document.getElementById("billTo").value,
        shipTo: document.getElementById("shipTo").value,
        gstin: document.getElementById("gstin").value,
        items: items,
        subtotal: document.getElementById("subtotal").value,
        received: document.getElementById("receivedAmount").value,
        balance: document.getElementById("balanceDue").value
    };

    fetch("/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "invoice.pdf";
        a.click();
    });
}

let savedCustomers = [];

function loadCustomers() {
    fetch("/customers")
        .then(response => response.json())
        .then(data => {
            savedCustomers = data.customers || [];

            const select = document.getElementById("customerSelect");
            if (!select) return;

            select.innerHTML = `<option value="">-- Select Customer --</option>`;

            savedCustomers.forEach((customer, index) => {
                const option = document.createElement("option");
                option.value = index;
                option.textContent = customer.bill_to;
                select.appendChild(option);
            });
        });
}

function autofillCustomer() {
    const select = document.getElementById("customerSelect");
    const index = select.value;

    if (index === "") return;

    const customer = savedCustomers[index];
    if (!customer) return;

    document.getElementById("billTo").value = customer.bill_to || "";
    document.getElementById("shipTo").value = customer.ship_to || "";
    document.getElementById("gstin").value = customer.gstin || "";
};