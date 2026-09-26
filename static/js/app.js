/**
 * StockSense - Product Management Frontend Interaction Script
 * Beginner-friendly vanilla JavaScript for modal dialogs, client-side validation,
 * and real-time search table filtering.
 */

// --- 1. MODAL DIALOG CONTROLLERS ---

function openAddModal() {
    const modal = document.getElementById("addModal");
    if (modal) {
        modal.classList.add("active");
        document.getElementById("add_name").focus();
    }
}

function closeAddModal() {
    const modal = document.getElementById("addModal");
    if (modal) {
        modal.classList.remove("active");
    }
}

function openEditModal(id, name, sku, category, unit, initialStock, reorderLevel) {
    const modal = document.getElementById("editModal");
    const form = document.getElementById("editProductForm");

    if (modal && form) {
        // Set form action dynamically to target the specific product ID
        form.action = `/products/edit/${id}`;

        // Pre-fill edit modal input fields
        document.getElementById("edit_name").value = name;
        document.getElementById("edit_sku").value = sku;
        document.getElementById("edit_category").value = category;
        document.getElementById("edit_unit").value = unit;
        document.getElementById("edit_initial_stock").value = initialStock;
        document.getElementById("edit_reorder_level").value = reorderLevel;

        modal.classList.add("active");
        document.getElementById("edit_name").focus();
    }
}

function closeEditModal() {
    const modal = document.getElementById("editModal");
    if (modal) {
        modal.classList.remove("active");
    }
}

function openDeleteModal(id, name, sku) {
    const modal = document.getElementById("deleteModal");
    const form = document.getElementById("deleteProductForm");
    const nameSpan = document.getElementById("deleteProductName");
    const skuSpan = document.getElementById("deleteProductSku");

    if (modal && form) {
        form.action = `/products/delete/${id}`;
        nameSpan.textContent = name;
        skuSpan.textContent = sku;
        modal.classList.add("active");
    }
}

function closeDeleteModal() {
    const modal = document.getElementById("deleteModal");
    if (modal) {
        modal.classList.remove("active");
    }
}

// Close modals when clicking on the dark backdrop or pressing Escape key
window.addEventListener("click", function(event) {
    if (event.target.classList.contains("modal-overlay")) {
        closeAddModal();
        closeEditModal();
        closeDeleteModal();
    }
});

window.addEventListener("keydown", function(event) {
    if (event.key === "Escape") {
        closeAddModal();
        closeEditModal();
        closeDeleteModal();
    }
});


// --- 2. CLIENT-SIDE FORM VALIDATION ---

function validateProductForm(form) {
    const name = form.querySelector('[name="name"]').value.trim();
    const sku = form.querySelector('[name="sku"]').value.trim();
    const category = form.querySelector('[name="category"]').value.trim();
    const unit = form.querySelector('[name="unit"]').value;
    const initialStock = parseFloat(form.querySelector('[name="initial_stock"]').value);
    const reorderLevel = parseFloat(form.querySelector('[name="reorder_level"]').value);

    // Validate required fields
    if (!name || !sku || !category || !unit) {
        alert("Please fill in all required fields (Name, SKU, Category, and Unit).");
        return false;
    }

    // Validate stock and reorder level cannot be negative
    if (isNaN(initialStock) || initialStock < 0) {
        alert("Initial Stock cannot be negative or invalid.");
        return false;
    }

    if (isNaN(reorderLevel) || reorderLevel < 0) {
        alert("Reorder Level cannot be negative or invalid.");
        return false;
    }

    return true;
}


// --- 3. REAL-TIME CLIENT-SIDE SEARCH FILTER ---

function quickFilterTable() {
    const input = document.getElementById("tableSearchInput");
    if (!input) return;

    const filter = input.value.toLowerCase().trim();
    const rows = document.querySelectorAll(".product-row");
    let visibleCount = 0;

    rows.forEach(row => {
        const name = row.getAttribute("data-name") || "";
        const sku = row.getAttribute("data-sku") || "";

        if (name.includes(filter) || sku.includes(filter)) {
            row.style.display = "";
            visibleCount++;
        } else {
            row.style.display = "none";
        }
    });
}
