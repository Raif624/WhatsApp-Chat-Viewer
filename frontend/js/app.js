/* ==========================================
   WHATSAPP CHAT VIEWER
   COMPLETE MULTI-CHAT FRONTEND
   Images, videos, audio, PDFs and documents
========================================== */


/* ==========================================
   1. API CONFIGURATION
========================================== */


const API_BASE_URL = "https://whatsapp-chat-viewer-psx8.onrender.com";

/* ==========================================
   2. SELECT MAIN HTML ELEMENTS
========================================== */

const chatList = document.getElementById("chatList");
const messageContainer = document.getElementById("messageContainer");
const chatSearch = document.getElementById("chatSearch");
const senderFilter = document.getElementById("senderFilter");
const dateFilter = document.getElementById("dateFilter");
const clearDateBtn = document.getElementById("clearDateBtn");
const contactName = document.getElementById("contactName");
const headerAvatar = document.querySelector(".chat-header .profile-avatar");


/* ==========================================
   3. APPLICATION DATA
========================================== */

let allChats = [];
let chatMessages = [];
let selectedChatId = null;
let selectedChatName = null;


/* ==========================================
   AUTHENTICATION HELPER
========================================== */

async function getAuthHeaders() {
    const { data, error } =
        await window.supabaseClient.auth.getSession();

    if (error || !data.session) {
        window.location.href = "login.html";
        throw new Error("Authentication required. Please log in.");
    }

    return {
        "Authorization": `Bearer ${data.session.access_token}`
    };
}


/* ==========================================
   4. LOAD ALL CONVERSATIONS
========================================== */

async function loadChats() {
    try {
        console.log("Loading conversations...");

        const response = await fetch(
            `${API_BASE_URL}/api/chats`,
            {
                headers: await getAuthHeaders()
            }
        );

        if (!response.ok) {
            throw new Error(`Unable to load chats: ${response.status}`);
        }

        const data = await response.json();

        allChats = Array.isArray(data.chats) ? data.chats : [];

        console.log("Total chats:", allChats.length);

        renderChatList();

        if (allChats.length > 0) {
            // Keep the selected conversation if it still exists.
            const currentChatExists = allChats.some(
                chat => chat.chat_id === selectedChatId
            );

            const chatToOpen = currentChatExists
                ? selectedChatId
                : allChats[0].chat_id;

            await loadSelectedChat(chatToOpen);
        } else {
            selectedChatId = null;
            selectedChatName = null;
            chatMessages = [];

            if (contactName) contactName.textContent = "Select a chat";
            if (headerAvatar) headerAvatar.textContent = "?";

            messageContainer.textContent = "No conversations imported yet.";
        }
    } catch (error) {
        console.error("Chat list loading error:", error);
        chatList.textContent = "Unable to load conversations.";
        messageContainer.textContent =
            "Unable to connect to the Flask server. Make sure Flask is running.";
    }
}


/* ==========================================
   5. DISPLAY CHAT LIST IN SIDEBAR
========================================== */

function renderChatList() {
    chatList.replaceChildren();

    allChats.forEach(function(chat) {
        const chatItem = document.createElement("div");
        chatItem.className = "chat-item";

        if (chat.chat_id === selectedChatId) {
            chatItem.classList.add("active");
        }

        const avatar = document.createElement("div");
        avatar.className = "profile-avatar";
        avatar.textContent = (chat.chat_name || "?").charAt(0).toUpperCase();

        const chatInfo = document.createElement("div");
        chatInfo.className = "chat-info";

        const name = document.createElement("h3");
        name.textContent = chat.chat_name || "Unnamed chat";

        const preview = document.createElement("p");
        preview.textContent = chat.last_message || "No messages";

        chatInfo.appendChild(name);
        chatInfo.appendChild(preview);

        chatItem.appendChild(avatar);
        chatItem.appendChild(chatInfo);

        chatItem.addEventListener("click", function() {
            loadSelectedChat(chat.chat_id);
        });

        chatList.appendChild(chatItem);
    });
}


/* ==========================================
   6. LOAD SELECTED CONVERSATION
========================================== */

async function loadSelectedChat(chatId) {
    try {
        console.log("Loading selected conversation:", chatId);

        const response = await fetch(
            `${API_BASE_URL}/api/chats/${encodeURIComponent(chatId)}`,
            {
                headers: await getAuthHeaders()
            }
        );

        if (!response.ok) {
            throw new Error(`Unable to load messages: ${response.status}`);
        }

        const data = await response.json();

        selectedChatId = data.chat_id;
        selectedChatName = data.chat_name;
        chatMessages = Array.isArray(data.messages) ? data.messages : [];

        contactName.textContent = selectedChatName || "Unknown chat";

        if (headerAvatar) {
            headerAvatar.textContent =
                (selectedChatName || "?").charAt(0).toUpperCase();
        }

        // Reset filters when switching conversations.
        chatSearch.value = "";
        senderFilter.value = "all";
        dateFilter.value = "";

        renderChatList();
        renderMessages(chatMessages);

        console.log("Messages loaded:", chatMessages.length);
    } catch (error) {
        console.error("Message loading error:", error);
        messageContainer.textContent =
            "Unable to load this conversation. Check the Flask server and chat data.";
    }
}


/* ==========================================
   7. FORMAT MESSAGE TIME AND DATE
========================================== */

function formatTime(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
    });
}


function formatDate(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "Unknown date";
    }

    return date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric"
    });
}


/* ==========================================
   8. DATE SEPARATOR AND SYSTEM MESSAGE
========================================== */

function createDateSeparator(timestamp) {
    const separator = document.createElement("div");
    separator.className = "date-separator";

    const dateText = document.createElement("span");
    dateText.textContent = formatDate(timestamp);

    separator.appendChild(dateText);
    return separator;
}


function createSystemMessage(message) {
    const systemElement = document.createElement("div");
    systemElement.className = "system-message";
    systemElement.textContent = message.message || "";

    return systemElement;
}


/* ==========================================
   9. MEDIA URL AND FILE HELPERS
========================================== */

function getMediaURL(filename) {
    if (!selectedChatId) {
        throw new Error("No conversation is selected.");
    }

    return (
        `${API_BASE_URL}/api/media/` +
        `${encodeURIComponent(selectedChatId)}/` +
        `${encodeURIComponent(filename)}`
    );
}


// Media routes require a bearer token. HTML media elements and ordinary
// anchor links cannot attach that token, so fetch the file and use a Blob URL.
const mediaObjectURLCache = new Map();

async function getAuthenticatedMediaObjectURL(filename) {
    if (!selectedChatId) {
        throw new Error("No conversation is selected.");
    }

    const cacheKey = `${selectedChatId}/${filename}`;

    if (mediaObjectURLCache.has(cacheKey)) {
        return mediaObjectURLCache.get(cacheKey);
    }

    const response = await fetch(getMediaURL(filename), {
        headers: await getAuthHeaders()
    });

    if (!response.ok) {
        throw new Error(`Unable to load attachment: ${response.status}`);
    }

    const mediaBlob = await response.blob();
    const objectURL = URL.createObjectURL(mediaBlob);
    mediaObjectURLCache.set(cacheKey, objectURL);

    return objectURL;
}


async function openAuthenticatedMedia(filename) {
    const objectURL = await getAuthenticatedMediaObjectURL(filename);
    window.open(objectURL, "_blank", "noopener");
}


function createDownloadLink(url, filename) {
    const link = document.createElement("a");

    link.href = "#";
    link.className = "media-download-btn";
    link.textContent = "⬇ Download";

    link.addEventListener("click", async function(event) {
        event.preventDefault();

        try {
            const objectURL =
                await getAuthenticatedMediaObjectURL(filename);

            const downloadLink = document.createElement("a");
            downloadLink.href = objectURL;
            downloadLink.download = filename;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            downloadLink.remove();
        } catch (error) {
            console.error("Attachment download error:", error);
            alert(error.message || "Unable to download this attachment.");
        }
    });

    return link;
}


function createFilenameLabel(filename) {
    const label = document.createElement("div");
    label.className = "media-filename";
    label.textContent = filename;

    return label;
}


function createUnavailableMessage(text) {
    const element = document.createElement("div");
    element.className = "media-unavailable";
    element.textContent = text;

    return element;
}


function createDocumentCard(filename, type, url) {
    const card = document.createElement("div");
    card.className = "document-card";

    const icon = document.createElement("div");
    icon.className = "document-icon";
    icon.textContent = type === "PDF document" ? "📕" : "📄";

    const info = document.createElement("div");
    info.className = "document-info";

    const name = createFilenameLabel(filename);

    const description = document.createElement("small");
    description.textContent = type;

    info.appendChild(name);
    info.appendChild(description);

    const actions = document.createElement("div");
    actions.className = "document-actions";

    const openLink = document.createElement("a");
    openLink.href = "#";
    openLink.textContent = "Open";
    openLink.className = "document-open-btn";

    openLink.addEventListener("click", async function(event) {
        event.preventDefault();

        try {
            await openAuthenticatedMedia(filename);
        } catch (error) {
            console.error("Attachment open error:", error);
            alert(error.message || "Unable to open this attachment.");
        }
    });

    actions.appendChild(openLink);
    actions.appendChild(createDownloadLink(url, filename));

    card.appendChild(icon);
    card.appendChild(info);
    card.appendChild(actions);

    return card;
}


/* ==========================================
   10. FIND ATTACHMENT IN EXPORTED MESSAGE
========================================== */

function findAttachmentFilename(messageText) {
    const extensions = [
        "jpg", "jpeg", "png", "gif", "webp",
        "mp4", "3gp", "mov", "webm",
        "opus", "ogg", "mp3", "m4a", "aac", "wav",
        "pdf", "doc", "docx", "xls", "xlsx",
        "ppt", "pptx", "txt", "vcf", "zip"
    ];

    const extensionPattern = extensions.join("|");

    // Match a filename ending in a supported extension.
    // The lookahead allows WhatsApp's "(file attached)" suffix.
    const regex = new RegExp(
        `([\\w .()\\-]+\\.(${extensionPattern}))(?=\\s*(?:\\(file attached\\))?\\s*$)`,
        "i"
    );

    const match = String(messageText || "").match(regex);

    return match ? match[1].trim() : null;
}


/* ==========================================
   11. CREATE MESSAGE BUBBLE WITH MEDIA
========================================== */

function createMessageBubble(message) {
    const messageWrapper = document.createElement("div");

    messageWrapper.className = message.is_mine
        ? "message-row outgoing"
        : "message-row incoming";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    const messageContent = message.message || "";
    const filename = findAttachmentFilename(messageContent);

    if (filename) {
        const extension = filename.split(".").pop().toLowerCase();
        const mediaURL = getMediaURL(filename);

        // IMAGE
        if (["jpg", "jpeg", "png", "gif", "webp"].includes(extension)) {
            const image = document.createElement("img");

            image.alt = filename;
            image.className = "chat-image";
            image.loading = "lazy";

            image.addEventListener("click", function() {
                openImagePreview(filename);
            });

            getAuthenticatedMediaObjectURL(filename)
                .then(objectURL => {
                    image.src = objectURL;
                })
                .catch(error => {
                    console.error("Image loading error:", error);
                    image.replaceWith(
                        createUnavailableMessage(`Image unavailable: ${filename}`)
                    );
                });

            image.addEventListener("error", function() {
                image.replaceWith(
                    createUnavailableMessage(`Image unavailable: ${filename}`)
                );
            });

            bubble.appendChild(image);
            bubble.appendChild(createFilenameLabel(filename));
            bubble.appendChild(createDownloadLink(mediaURL, filename));
        }

        // VIDEO
        else if (["mp4", "3gp", "mov", "webm"].includes(extension)) {
            const video = document.createElement("video");

            video.controls = true;
            video.preload = "metadata";
            video.playsInline = true;
            video.className = "chat-video";

            video.addEventListener("error", function() {
                video.replaceWith(
                    createUnavailableMessage(
                        `Video cannot be played in this browser: ${filename}`
                    )
                );
            });

            getAuthenticatedMediaObjectURL(filename)
                .then(objectURL => {
                    video.src = objectURL;
                })
                .catch(error => {
                    console.error("Video loading error:", error);
                    video.replaceWith(
                        createUnavailableMessage(`Video unavailable: ${filename}`)
                    );
                });

            bubble.appendChild(video);
            bubble.appendChild(createFilenameLabel(filename));
            bubble.appendChild(createDownloadLink(mediaURL, filename));
        }

        // AUDIO / WHATSAPP VOICE NOTES
        else if (
            ["opus", "ogg", "mp3", "m4a", "aac", "wav"].includes(extension)
        ) {
            const audioTitle = createFilenameLabel(`🎤 ${filename}`);

            const audio = document.createElement("audio");
            audio.controls = true;
            audio.preload = "metadata";
            audio.className = "chat-audio";

            audio.addEventListener("error", function() {
                audioTitle.textContent =
                    `Audio cannot be played in this browser: ${filename}`;
            });

            getAuthenticatedMediaObjectURL(filename)
                .then(objectURL => {
                    audio.src = objectURL;
                })
                .catch(error => {
                    console.error("Audio loading error:", error);
                    audioTitle.textContent =
                        `Audio unavailable: ${filename}`;
                });

            bubble.appendChild(audioTitle);
            bubble.appendChild(audio);
            bubble.appendChild(createDownloadLink(mediaURL, filename));
        }

        // PDF
        else if (extension === "pdf") {
            bubble.appendChild(
                createDocumentCard(filename, "PDF document", mediaURL)
            );
        }

        // OTHER DOCUMENTS
        else {
            bubble.appendChild(
                createDocumentCard(filename, "Document", mediaURL)
            );
        }
    } else if (message.type === "media") {
        const attachment = document.createElement("div");
        attachment.className = "message-text";
        attachment.textContent = `📎 ${messageContent}`;
        bubble.appendChild(attachment);
    } else if (message.type === "empty") {
        const emptyText = document.createElement("div");
        emptyText.className = "message-text";
        emptyText.textContent = "Empty message";
        bubble.appendChild(emptyText);
    } else {
        const text = document.createElement("div");
        text.className = "message-text";
        text.textContent = messageContent;
        bubble.appendChild(text);
    }

    const timestamp = document.createElement("span");
    timestamp.className = "message-time";
    timestamp.textContent = formatTime(message.timestamp);

    bubble.appendChild(timestamp);
    messageWrapper.appendChild(bubble);

    return messageWrapper;
}


/* ==========================================
   12. RENDER ALL MESSAGES
========================================== */

function renderMessages(messages) {
    messageContainer.replaceChildren();

    let previousDate = null;

    messages.forEach(function(message) {
        const timestamp = message.timestamp || "";
        const currentDate = timestamp.split("T")[0];

        if (currentDate !== previousDate) {
            messageContainer.appendChild(
                createDateSeparator(timestamp)
            );

            previousDate = currentDate;
        }

        if (message.type === "system") {
            messageContainer.appendChild(
                createSystemMessage(message)
            );
        } else {
            messageContainer.appendChild(
                createMessageBubble(message)
            );
        }
    });

    messageContainer.scrollTop = messageContainer.scrollHeight;
}


/* ==========================================
   13. SEARCH AND FILTER MESSAGES
========================================== */

function applyFilters() {
    const searchText = chatSearch.value.trim().toLowerCase();
    const selectedSender = senderFilter.value;
    const selectedDate = dateFilter.value;

    const filteredMessages = chatMessages.filter(function(message) {
        const messageText = (message.message || "").toLowerCase();
        const senderName = (message.sender || "").toLowerCase();

        const matchesSearch =
            messageText.includes(searchText) ||
            senderName.includes(searchText);

        let matchesSender = false;

        if (selectedSender === "all") {
            matchesSender = true;
        } else if (selectedSender === "me") {
            matchesSender = message.is_mine === true;
        } else if (selectedSender === "other") {
            matchesSender =
                message.sender === selectedChatName;
        } else if (selectedSender === "system") {
            matchesSender = message.type === "system";
        }

        const messageDate = (message.timestamp || "").split("T")[0];

        const matchesDate =
            selectedDate === "" ||
            messageDate === selectedDate;

        return matchesSearch && matchesSender && matchesDate;
    });

    renderMessages(filteredMessages);

    if (filteredMessages.length === 0) {
        const noResults = document.createElement("div");
        noResults.className = "no-results";
        noResults.textContent = "No matching messages found.";
        messageContainer.appendChild(noResults);
    }

    if (selectedDate !== "" && filteredMessages.length > 0) {
        messageContainer.scrollTop = 0;
    }
}


/* ==========================================
   14. SEARCH AND FILTER EVENT LISTENERS
========================================== */

chatSearch.addEventListener("input", applyFilters);
senderFilter.addEventListener("change", applyFilters);
dateFilter.addEventListener("change", applyFilters);

clearDateBtn.addEventListener("click", function() {
    dateFilter.value = "";
    applyFilters();
});


/* ==========================================
   15. IMAGE PREVIEW MODAL
========================================== */

const imagePreviewModal =
    document.getElementById("imagePreviewModal");

const previewImage =
    document.getElementById("previewImage");

const closeImagePreview =
    document.getElementById("closeImagePreview");

const downloadPreviewImage =
    document.getElementById("downloadPreviewImage");


async function openImagePreview(filename) {
    try {
        const objectURL =
            await getAuthenticatedMediaObjectURL(filename);

        if (
            !imagePreviewModal ||
            !previewImage ||
            !downloadPreviewImage
        ) {
            // Open the already-authenticated Blob URL as a fallback.
            window.open(objectURL, "_blank", "noopener");
            return;
        }

        previewImage.src = objectURL;
        previewImage.alt = filename;

        downloadPreviewImage.href = objectURL;
        downloadPreviewImage.download = filename;

        imagePreviewModal.classList.remove("hidden");
    } catch (error) {
        console.error("Image preview error:", error);
        alert(error.message || "Unable to preview this image.");
    }
}


function closePreview() {
    if (!imagePreviewModal || !previewImage) return;

    imagePreviewModal.classList.add("hidden");
    previewImage.src = "";
}


if (closeImagePreview) {
    closeImagePreview.addEventListener("click", closePreview);
}

if (imagePreviewModal) {
    imagePreviewModal.addEventListener("click", function(event) {
        if (event.target === imagePreviewModal) {
            closePreview();
        }
    });
}

document.addEventListener("keydown", function(event) {
    if (event.key === "Escape") {
        closePreview();
    }
});


/* ==========================================
   16. IMPORT MODAL ELEMENTS
========================================== */

const importChatBtn = document.getElementById("importChatBtn");
const importModal = document.getElementById("importModal");
const closeImportBtn = document.getElementById("closeImportBtn");
const zipFileInput = document.getElementById("zipFileInput");
const previewZipBtn = document.getElementById("previewZipBtn");
const uploadSection = document.getElementById("uploadSection");
const previewSection = document.getElementById("previewSection");
const previewChatName = document.getElementById("previewChatName");
const previewTextFile = document.getElementById("previewTextFile");
const previewMessageInfo = document.getElementById("previewMessageInfo");
const previewMediaInfo = document.getElementById("previewMediaInfo");
const importStatus = document.getElementById("importStatus");
const cancelImportBtn = document.getElementById("cancelImportBtn");
const confirmImportBtn = document.getElementById("confirmImportBtn");

let currentImportPreview = null;


/* ==========================================
   17. OPEN AND CLOSE IMPORT MODAL
========================================== */

function openImportModal() {
    importModal.classList.remove("hidden");

    uploadSection.classList.remove("hidden");
    previewSection.classList.add("hidden");

    importStatus.textContent = "";
    zipFileInput.value = "";
    currentImportPreview = null;
}


function closeImportModal() {
    importModal.classList.add("hidden");

    zipFileInput.value = "";
    importStatus.textContent = "";
    currentImportPreview = null;
}


if (importChatBtn) {
    importChatBtn.addEventListener("click", openImportModal);
}

if (closeImportBtn) {
    closeImportBtn.addEventListener("click", closeImportModal);
}

if (cancelImportBtn) {
    cancelImportBtn.addEventListener("click", closeImportModal);
}


/* ==========================================
   18. PREVIEW SELECTED ZIP FILE
========================================== */

if (previewZipBtn) {
    previewZipBtn.addEventListener("click", async function() {
        const selectedFile = zipFileInput.files[0];

        if (!selectedFile) {
            importStatus.textContent =
                "Please select a WhatsApp ZIP file first.";
            return;
        }

        importStatus.textContent = "Inspecting ZIP file...";
        previewZipBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append("file", selectedFile);

            const response = await fetch(
                `${API_BASE_URL}/api/import/preview`,
                {
                    method: "POST",
                    headers: await getAuthHeaders(),
                    body: formData
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.message || "Unable to inspect ZIP file."
                );
            }

            currentImportPreview = data.preview;

            previewChatName.textContent =
                currentImportPreview.chat_name;

            previewTextFile.textContent =
                "Chat file: " + currentImportPreview.text_filename;

            previewMessageInfo.textContent =
                "Files found: " + currentImportPreview.total_files;

            previewMediaInfo.textContent =
                "Media attachments: " + currentImportPreview.media_count;

            uploadSection.classList.add("hidden");
            previewSection.classList.remove("hidden");

            importStatus.textContent =
                "ZIP inspection successful. Review before importing.";
        } catch (error) {
            console.error("ZIP preview error:", error);
            importStatus.textContent = error.message;
        } finally {
            previewZipBtn.disabled = false;
        }
    });
}


/* ==========================================
   19. CONFIRM CHAT IMPORT
========================================== */

if (confirmImportBtn) {
    confirmImportBtn.addEventListener("click", async function() {
        if (!currentImportPreview) {
            importStatus.textContent =
                "Please preview the ZIP file first.";
            return;
        }

        const selectedFile = zipFileInput.files[0];

        if (!selectedFile) {
            importStatus.textContent =
                "Please select the ZIP file again.";
            return;
        }

        confirmImportBtn.disabled = true;

        importStatus.textContent =
            "Importing conversation. Please wait...";

        try {
            const formData = new FormData();
            formData.append("file", selectedFile);

            const response = await fetch(
                `${API_BASE_URL}/api/import/confirm`,
                {
                    method: "POST",
                    headers: await getAuthHeaders(),
                    body: formData
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || "Import failed.");
            }

            importStatus.textContent = data.message || "Import successful.";

            console.log("Imported conversation:", data.chat);

            // Refresh sidebar and then open the newly imported conversation.
            await loadChats();

            if (data.chat && data.chat.chat_id) {
                await loadSelectedChat(data.chat.chat_id);
            }

            closeImportModal();
        } catch (error) {
            console.error("Import error:", error);
            importStatus.textContent = error.message;
        } finally {
            confirmImportBtn.disabled = false;
        }
    });
}


/* ==========================================
   20. INITIALIZE APPLICATION
========================================== */

loadChats();



/* ==========================================
   SETTINGS MENU AND SUPABASE LOGOUT
========================================== */

const settingsBtn = document.getElementById("settingsBtn");

if (settingsBtn) {
    // Give the existing gear button an accessible label and menu state.
    settingsBtn.setAttribute("aria-label", "Settings");
    settingsBtn.setAttribute("aria-haspopup", "menu");
    settingsBtn.setAttribute("aria-expanded", "false");

    // Add menu styling without requiring changes to the existing CSS file.
    if (!document.getElementById("settingsMenuStyles")) {
        const settingsStyle = document.createElement("style");
        settingsStyle.id = "settingsMenuStyles";
        settingsStyle.textContent = `
            .settings-menu {
                position: absolute;
                top: calc(100% + 8px);
                right: 0;
                z-index: 1000;
                min-width: 190px;
                padding: 8px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
            }
            .settings-menu[hidden] {
                display: none;
            }
            .settings-menu-title {
                padding: 8px 10px;
                color: #64748b;
                font-size: 12px;
                font-weight: 600;
            }
            .settings-logout-btn {
                display: flex;
                align-items: center;
                gap: 10px;
                width: 100%;
                padding: 10px;
                border: 0;
                border-radius: 7px;
                background: transparent;
                color: #b42318;
                font: inherit;
                text-align: left;
                cursor: pointer;
            }
            .settings-logout-btn:hover {
                background: #fef2f2;
            }
            .settings-logout-btn:disabled {
                opacity: 0.6;
                cursor: wait;
            }
            .sidebar-actions {
                position: relative;
            }
        `;
        document.head.appendChild(settingsStyle);
    }

    const settingsMenu = document.createElement("div");
    settingsMenu.id = "settingsMenu";
    settingsMenu.className = "settings-menu";
    settingsMenu.setAttribute("role", "menu");
    settingsMenu.hidden = true;

    const menuTitle = document.createElement("div");
    menuTitle.className = "settings-menu-title";
    menuTitle.textContent = "Account";

    const logoutBtn = document.createElement("button");
    logoutBtn.type = "button";
    logoutBtn.className = "settings-logout-btn";
    logoutBtn.setAttribute("role", "menuitem");
    logoutBtn.innerHTML = '<span aria-hidden="true">↪</span><span>Log out</span>';

    settingsMenu.append(menuTitle, logoutBtn);

    const settingsContainer =
        settingsBtn.closest(".sidebar-actions") || settingsBtn.parentElement;
    settingsContainer.appendChild(settingsMenu);

    function closeSettingsMenu() {
        settingsMenu.hidden = true;
        settingsBtn.setAttribute("aria-expanded", "false");
    }

    settingsBtn.addEventListener("click", function(event) {
        event.stopPropagation();
        const shouldOpen = settingsMenu.hidden;
        settingsMenu.hidden = !shouldOpen;
        settingsBtn.setAttribute("aria-expanded", String(shouldOpen));
    });

    settingsMenu.addEventListener("click", function(event) {
        event.stopPropagation();
    });

    document.addEventListener("click", function(event) {
        if (!settingsContainer.contains(event.target)) {
            closeSettingsMenu();
        }
    });

    document.addEventListener("keydown", function(event) {
        if (event.key === "Escape") {
            closeSettingsMenu();
        }
    });

    logoutBtn.addEventListener("click", async function() {
        logoutBtn.disabled = true;
        logoutBtn.querySelector("span:last-child").textContent = "Logging out...";

        try {
            const { error } = await window.supabaseClient.auth.signOut();

            if (error) {
                throw error;
            }

            // Clear any cached authenticated media URLs from this page.
            if (typeof mediaObjectURLCache !== "undefined") {
                for (const objectURL of mediaObjectURLCache.values()) {
                    URL.revokeObjectURL(objectURL);
                }
                mediaObjectURLCache.clear();
            }

            window.location.replace("login.html");
        } catch (error) {
            console.error("Logout error:", error);
            alert(error.message || "Unable to log out. Please try again.");
            logoutBtn.disabled = false;
            logoutBtn.querySelector("span:last-child").textContent = "Log out";
        }
    });
}
