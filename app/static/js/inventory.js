/**
 * LifeFlow Real-time Inventory Polling Engine.
 * Lightweight vanilla JavaScript client-side polling every 10 seconds.
 * Strictly adheres to stack constraints (no WebSockets/Socket.IO).
 */

document.addEventListener('DOMContentLoaded', () => {
  const inventoryGrid = document.getElementById('inventory-grid');
  const totalUnitsEl = document.getElementById('total-units-count');
  const lastUpdatedEl = document.getElementById('last-updated-time');
  const refreshBtn = document.getElementById('manual-refresh-btn');

  let lastCounts = {};

  async function fetchInventory() {
    try {
      if (refreshBtn) refreshBtn.classList.add('loading');

      const response = await fetch('/api/inventory');
      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();
      if (!data.success) throw new Error(data.error || 'Failed to fetch inventory');

      updateUI(data);

      if (lastUpdatedEl) {
        const now = new Date();
        lastUpdatedEl.textContent = now.toLocaleTimeString();
      }
    } catch (err) {
      console.error('Error polling inventory:', err);
    } finally {
      if (refreshBtn) refreshBtn.classList.remove('loading');
    }
  }

  function updateUI(data) {
    if (totalUnitsEl && data.total_units !== undefined) {
      totalUnitsEl.textContent = data.total_units;
    }

    const inventory = data.inventory;
    if (!inventory) return;

    for (const [bloodType, item] of Object.entries(inventory)) {
      const card = document.getElementById(`blood-card-${bloodType.replace('+', 'pos').replace('-', 'neg')}`);
      const countEl = document.getElementById(`count-${bloodType.replace('+', 'pos').replace('-', 'neg')}`);

      if (countEl && card) {
        const prevCount = lastCounts[bloodType];
        const newCount = item.count;

        countEl.textContent = newCount;

        // Visual highlight micro-animation on delta change
        if (prevCount !== undefined && prevCount !== newCount) {
          card.classList.remove('pulse-update');
          void card.offsetWidth; // Trigger reflow
          card.classList.add('pulse-update');
        }

        // Update card color classes
        card.classList.remove('critical', 'low', 'adequate');
        card.classList.add(item.status);

        lastCounts[bloodType] = newCount;
      }
    }
  }

  // Initial fetch
  fetchInventory();

  // Polling interval: every 10 seconds
  const POLL_INTERVAL_MS = 10000;
  setInterval(fetchInventory, POLL_INTERVAL_MS);

  // Manual refresh button listener
  if (refreshBtn) {
    refreshBtn.addEventListener('click', (e) => {
      e.preventDefault();
      fetchInventory();
    });
  }
});
