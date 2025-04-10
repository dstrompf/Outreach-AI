
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyCW2hvzF-Ugoy9IbYSVbp0gyT-vQ16LBKg",
  authDomain: "ai-outreach-tool-4f9f0.firebaseapp.com",
  projectId: "ai-outreach-tool-4f9f0",
  storageBucket: "ai-outreach-tool-4f9f0.firebasestorage.app",
  messagingSenderId: "301479745716",
  appId: "1:301479745716:web:2d364b7b3983f4e9349fe1",
  measurementId: "G-4E3DH0RQLZ"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
export const auth = getAuth(app);
export const db = getFirestore(app);
