// ===========================================
// firebase-config.js
// Firebase project: chatbot-7c691
// ===========================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyDdViJsTRq12gSrfgbmxyTY6qtBBviD4Dk",
  authDomain: "chatbot-7c691.firebaseapp.com",
  projectId: "chatbot-7c691",
  storageBucket: "chatbot-7c691.firebasestorage.app",
  messagingSenderId: "576961124343",
  appId: "1:576961124343:web:1eb6d00c8b90ded2bc00f2",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
