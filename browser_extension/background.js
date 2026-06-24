// Background service worker for Student Focus Activity Tracker
// Works in Chrome / Edge (Manifest V3).

const SERVER_URL = "http://127.0.0.1:8765/active-tab";
const POLL_INTERVAL_SEC = 5;

function isValidHttpUrl(url) {
  if (!url) return false;
  return url.startsWith("http://") || url.startsWith("https://");
}

function sendActiveTabInfo(tab) {
  if (!tab || !tab.url || !isValidHttpUrl(tab.url)) {
    return;
  }

  const payload = {
    url: tab.url,
    title: tab.title || ""
  };

  fetch(SERVER_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }).catch(() => {
    // Silently ignore errors (e.g., Python app not running)
  });
}

function captureCurrentTab() {
  chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
    if (chrome.runtime.lastError) {
      return;
    }
    if (!tabs || !tabs.length) {
      return;
    }
    sendActiveTabInfo(tabs[0]);
  });
}

// Tab activated (user switches between tabs)
chrome.tabs.onActivated.addListener(() => {
  captureCurrentTab();
});

// Tab updated (URL changes, navigation, reload, etc.)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    sendActiveTabInfo(tab);
  }
});

// Window focus changes (user switches between windows)
chrome.windows.onFocusChanged.addListener(() => {
  captureCurrentTab();
});

// Periodic polling as backup
chrome.alarms.create("pollActiveTab", { periodInMinutes: POLL_INTERVAL_SEC / 60 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "pollActiveTab") {
    captureCurrentTab();
  }
});

// Initial capture when extension starts
captureCurrentTab();

