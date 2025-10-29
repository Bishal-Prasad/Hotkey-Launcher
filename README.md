# ⚡ Hotkey Launcher

**Hotkey Launcher** is a lightweight and customizable tool that lets you **launch apps, scripts, or websites instantly using keyboard shortcuts (hotkeys)**.  
It’s designed to save time and streamline your workflow by mapping your favorite key combinations to frequently used actions.

---

## 🚀 Features

✅ **Customizable Hotkeys** – Assign any key combination to any action (like opening an app, folder, or URL).  
✅ **Lightweight & Fast** – Runs quietly in the background with minimal CPU use.  
✅ **Cross-App Support** – Works system-wide, no matter which window is active.  

---

## 🧩 Example Setup

Let’s say you want:

| Action | Hotkey | Command |
|:-------|:--------|:--------|
| Open Notepad | `Ctrl + Alt + N` | `notepad.exe` |
| Open Chrome | `Ctrl + Alt + G` | `"C:\Program Files\Google\Chrome\Application\chrome.exe"` |
| Open YouTube | `Ctrl + Alt + Y` | `https://youtube.com` |

You can define these inside your configuration file (for example `launcher_config.json`):

```json
{
    "Ctrl+Alt+N": "notepad.exe",
    "Ctrl+Alt+G": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "Ctrl+Alt+Y": "https://youtube.com"
}
