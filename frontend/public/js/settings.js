// Settings page template
export function renderSettings() {
  return `
    <div class="page" id="settings-page">
      <div class="settings-group">
        <h3 class="settings-title">General Settings</h3>
        <div class="settings-item">
          <label for="vault-name">Vault Name</label>
          <input type="text" id="vault-name" value="My Piggy Bank" class="settings-input">
        </div>
        <div class="settings-item">
          <label for="capacity-limit">Capacity Limit (฿)</label>
          <input type="number" id="capacity-limit" value="500" class="settings-input">
        </div>
      </div>

      <div class="settings-group">
        <h3 class="settings-title">Notifications</h3>
        <div class="settings-item">
          <label for="alert-full">
            <input type="checkbox" id="alert-full" checked>
            Alert when vault is full
          </label>
        </div>
        <div class="settings-item">
          <label for="alert-deposit">
            <input type="checkbox" id="alert-deposit" checked>
            Alert on deposit
          </label>
        </div>
      </div>

      <div class="settings-group danger-zone">
        <h3 class="settings-title" style="color: #EF4444;">Danger Zone</h3>
        <button class="btn-danger">Reset Vault</button>
        <p class="danger-note">This action cannot be undone</p>
      </div>
    </div>
  `;
}
