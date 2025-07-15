import { useEffect, useState, useRef } from "react"
import { fetchAuthSession, fetchUserAttributes, signIn, signUp , confirmSignUp} from "aws-amplify/auth"
import { Authenticator, Button, View } from "@aws-amplify/ui-react"
import { Amplify } from "aws-amplify"
import { generateClient } from "aws-amplify/data"

import { API } from "../WingSightMain/WingSightMain.jsx"

import "@aws-amplify/ui-react/styles.css"
import "./App.css"
import WingSightMain from "../WingSightMain/WingSightMain"

// Add debugging to window object for browser inspection
window.WINGSIGHT_DEBUG = {
  env: import.meta.env || {},
  configAttempts: []
};

// Import configuration safely with multiple fallbacks
let amplifyConfig;

// Function to load the Amplify configuration
function loadAmplifyConfig() {
  try {
    // First, try to load from window.AMPLIFY_AUTH_CONFIG (set by build scripts)
    if (window.AMPLIFY_AUTH_CONFIG && 
        window.AMPLIFY_AUTH_CONFIG.auth?.Cognito?.userPoolId) {
      return {
        Auth: {
          Cognito: {
            ...window.AMPLIFY_AUTH_CONFIG.auth.Cognito
          }
        }
      };
    }
    
    // Second, try loading from amplify_outputs.json (from Amplify Gen 2)
    try {
      const configFile = require("../../amplify_outputs.json");
      
      if (configFile.Auth?.Cognito?.userPoolId) {
        return configFile; 
      }
    } catch (e) {
      console.warn("Failed to load amplify_outputs.json:", e);
    }
    
    // Third, try environment variables
    const region = import.meta.env.VITE_AWS_REGION || 'us-east-1';
    const userPoolId = import.meta.env.VITE_USER_POOL_ID;
    const userPoolClientId = import.meta.env.VITE_USER_POOL_CLIENT_ID;
    const identityPoolId = import.meta.env.VITE_IDENTITY_POOL_ID;
    
    if (userPoolId && userPoolClientId && identityPoolId) {
      return {
        Auth: {
          Cognito: {
            userPoolId,
            userPoolClientId,
            identityPoolId,
            region
          }
        }
      };
    }
    
    // Fallback to hardcoded configuration
    console.warn("Using fallback configuration - hardcoded values");
    return {
      Auth: {
        Cognito: {
          // Using values from your Terraform setup
          userPoolId: "us-east-1_SVl5j6Xb2",
          userPoolClientId: "4a4u87pug2egf25at6176cj5bs",
          identityPoolId: "us-east-1:079e3e93-26e1-4d59-87c3-5e0d2ffb4cf7",
          region: "us-east-1"
        }
      }
    };
  } catch (error) {
    console.error("Error loading Amplify configuration:", error);
    throw error;
  }
}

// Load the config and configure Amplify
amplifyConfig = loadAmplifyConfig();

// Save config to window for debugging
window.WINGSIGHT_DEBUG.amplifyConfig = amplifyConfig;

import "@aws-amplify/ui-react/styles.css"
import "./App.css"

// Configure Amplify with our settings
Amplify.configure(amplifyConfig);

const client = generateClient({
  authMode: "userPool"
});

export default function App() {
  const [username, setUsername] = useState("User");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userID, setUserID] = useState("");
  const [snsStatus, setSnsStatus] = useState("none"); // "none" | "pending" | "confirmed"
  const providedPasswordRef = useRef();

  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [notificationControl, setNotificationControl] = useState(null);

  // Check authentication status when component mounts
  useEffect(() => {
    const initializeAuthState = async () => {
      await checkAuthStatus();
    }
    initializeAuthState();
  }, []);


    // Function to check if user is authenticated
  const checkAuthStatus = async () => {
    try {
      // #TODO: Add check to backend session validation if needed
      const session = await fetchAuthSession();
      if (session && session.tokens) {
        setIsAuthenticated(true);
        await updateUsername();
        await fetchSnsStatus();
      }
    } catch (error) {
      setIsAuthenticated(false);
      console.error("User is not authenticated", error);
    }
  };

  /**
   * Form fields determine the structure of the Login and Signup forms.
   */
  const formFields = {
    signIn: {
      username: {
        order: 1,
        label: "Email",
        placeholder: "Enter your email"
      },
      password: {
        order: 2
      }
    },
    signUp: {
      username: {
        order: 1,
        label: "Email",
        placeholder: "Enter your email"
      },
      preferred_username: {
        order: 2,
        label: "Username",
        placeholder: "Choose a display name"
      },
      password: {
        order: 3
      },
      confirm_password: {
        order: 4
      }
    },
    resetPassword: {
      username: {
        order: 1,
        label: "Email",
        placeholder: "Enter your email"
      }
    }
  }

  const services = {
    async handleSignUp(input) {
      const userAtts = input.options.userAttributes;

      // Email is the username in Cognito but we also collect preferred_username
      const email = input.username; // Use username as email
      const displayName = userAtts.preferred_username || email.split('@')[0]; // Use preferred_username or extract from email

      providedPasswordRef.current = input.password;

      try {
        const output = await signUp(input);

        const userId = output.userId;
        setUserID(userId);
        setUsername(displayName);

        return output;
      } catch (error) {
        console.error("Sign up error:", error);
        throw error;
      }
    },

    async handleConfirmSignUp(input) {
      try {
        const username = input.username;
        const confirmationCode = input.confirmationCode;

        const signUpResult = await confirmSignUp({username, confirmationCode});

        const password = providedPasswordRef.current;

        const signInResult = await signIn({username, password});

        const attributes = await fetchUserAttributes();
        const userId = attributes.sub;

        setUserID(userId);

        await API.fetch(`add_user_with_id`, {
          body: JSON.stringify({
            username: username,
            email: attributes.email,
            user_id: userId,
          }),
        });

        await updateUsername();
        setIsAuthenticated(true);

        window.location.reload();

        return signInResult;
      } catch (error) {
        console.error("Confirmation/sign-in error:", error);
        throw error;
      }
    },

    async handleSignIn(input) {
      try {
        const output = await signIn(input);

        await updateUsername();
        setIsAuthenticated(true);

        return output;
      } catch (error) {
        console.error("Sign in error:", error);
        throw error;
      }
    }
  }

    // —— SNS helpers —— //

    async function fetchSnsStatus() {

      const attributes = await fetchUserAttributes();
      const sub = attributes.sub;

      const res = await API.fetch(
        `manage_subscription?user_id=${sub}`, {method: "GET"}
      );

      setSnsStatus(res.status);
    }


  // updates the current username
  const updateUsername = async () => {
    try {
      const user = await fetchUserAttributes();
      // #TODO: Backend - Fetch additional user profile data from backend
      const displayName = user.preferred_username || user.email.split('@')[0]; // Use preferred_username or extract from email
      setUserID(user.sub);
      setUsername(displayName);
    } catch (e) {
      console.error(`Error fetching user attributes: ${e}`);
    }
  }

  const handleSignOut = async (signOutFn) => {
    // #TODO: Backend - Update user's last active timestamp
    setUsername("User");
    setIsAuthenticated(false);
    return signOutFn();
  };

  // Called when user clicks the SNS button
  const handleSubscribe = async () => {
      const attributes = await fetchUserAttributes();
      const sub = attributes.sub;

      const res = await API.fetch(`manage_subscription`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: sub, action: "subscribe" }),
      });

      if (!res.status === "success"){
        alert("Error while subscribing");
        return;
      }
      toggleNotifications();
      await fetchSnsStatus();
    };

    // Map status → button label
  const labelMap = {
      none: "Subscribe to SNS",
      pending: "Resend Confirmation",
      confirmed: "Subscribed to SNS",
    };

    const toggleNotifications = () => {
      const isEnabling = !notificationsEnabled;
      setNotificationsEnabled(isEnabling);
  
      if (isEnabling) {
        notificationControl?.startNotifications();
      } else {
        notificationControl?.stopNotifications();
      }
    };


  return (
    <>
      <Authenticator formFields={formFields} services={services} initialState="signIn">
        {({ signOut }) => (
          <View className="app-container">
            <header className="app-header">
              <h1>WingSight - Welcome, {username}!</h1>
              <div style={{ display: "flex", gap: "1rem" }}>
              <Button
                colorTheme="primary"
                variation="link"
                onClick={handleSubscribe}
                isDisabled={snsStatus === "confirmed" || !isAuthenticated}
              >
                {labelMap[snsStatus]}
              </Button>

                <Button
                colorTheme="info" 
                variation="primary" 
                onClick={() => handleSignOut(signOut)}
                className="sign-out-button"
              >
                Sign Out
              </Button>
              </div>
            </header>
            
            <main className="app-main">
              <WingSightMain onRegisterNotificationControl={setNotificationControl}/>
            </main>
          </View>
        )}
      </Authenticator>
    </>
  )
}
