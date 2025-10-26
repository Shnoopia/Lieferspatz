function addZipCode() {
    const container = document.getElementById('zipCodeContainer');
    const div = document.createElement('div');
    div.className = 'zip-code-field';
    div.innerHTML = `
        <input type="text" name="delivery_zip_codes" placeholder="Enter delivery zip code">
        <button type="button" onclick="removeZipCode(this)"><i class="fas fa-trash-alt"></i></button>
    `;
    container.appendChild(div);
}

function removeZipCode(button) {
    const div = button.parentElement;
    div.remove();
}