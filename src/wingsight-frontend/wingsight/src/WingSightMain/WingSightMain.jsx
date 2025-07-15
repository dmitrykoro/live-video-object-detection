import { Button, Flex, SelectField, TextField, View, Card, Text, Heading, Divider, CheckboxField, Radio, Input, Label } from "@aws-amplify/ui-react"
import { useState, useEffect, useRef } from "react";
import { FaBell, FaTrash, FaTimes, FaHistory, FaPause, FaPlay } from 'react-icons/fa';
import { fetchAuthSession, fetchUserAttributes } from "aws-amplify/auth";
import { useAuthenticator } from '@aws-amplify/ui-react';   // <–– lets us know when sign‑in finishes …

// API utility functions
export const API = {
  // Get the base API URL from environment
  getBaseUrl: () => {
    const apiBaseUrl = import.meta.env.VITE_API_GATEWAY_URL || import.meta.env.VITE_WINGSIGHT_API_URL;
    if (!apiBaseUrl) {
      console.error("[API] API URL environment variable is not defined!");
      return "/v1"; // Default to relative URL if not set
    }
    // Remove trailing slashes
    return apiBaseUrl.replace(/\/+$/, '');
  },
  
  // Format endpoint URL based on API Gateway or direct URLs
  formatEndpoint: (endpoint) => {
    const baseUrl = API.getBaseUrl();
    const isApiGatewayUrl = baseUrl.includes('execute-api');
    
    // HTTP API Gateway (v2) has a different URL structure than REST API Gateway (v1)
    if (isApiGatewayUrl) { 
      // For HTTP API Gateway v2, URLs typically look like:
      // https://abcdef123.execute-api.region.amazonaws.com/stage
      // Add v1 prefix to endpoint for proper API Gateway routing
      if (baseUrl.endsWith('/')) {
        return `${baseUrl}v1/${endpoint}`;
      } else {
        return `${baseUrl}/v1/${endpoint}`;
      }
    } else {
      // For direct URLs to the backend (not through API Gateway)
      return `${baseUrl}/${endpoint}`;
    }
  },

  // Common fetch wrapper with auth and error handling
  fetch: async (endpoint, options = {}) => {
    try {
      // Always use POST for API Gateway to avoid CORS preflight issues
      if (!options.method) {
        options.method = "POST";
      }
      
      // Try to get auth session for token
      let headers = { 
        "Content-Type": "application/json",
        "Accept": "application/json"
      };
      
      try {
        const session = await fetchAuthSession();
        // Try different ways to access the token
        let token = null;
        
        // Method 1: Direct token access
        if (session?.tokens?.idToken?.toString) {
          token = session.tokens.idToken.toString();
        }
        // Method 2: JWT token from payload
        else if (session?.tokens?.idToken?.payload) {
          const payload = session.tokens.idToken.payload;
          const jwt = session.tokens.idToken.jwtToken;
          if (jwt) {
            token = jwt;
          }
        }
        // Method 3: Access token as fallback
        else if (session?.tokens?.accessToken?.toString) {
          token = session.tokens.accessToken.toString();
        }
        
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        } else {
          console.warn("[API] No token found in session:", session);
        }
      } catch (authError) {
        console.warn("[API] Could not fetch auth token:", authError);
      }

      // Format the endpoint URL
      const url = API.formatEndpoint(endpoint);

      // Make the API call with merged headers
      const response = await fetch(url, {
        ...options,
        headers: { ...headers, ...options.headers }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[API] Error ${response.status}: ${errorText}`);
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }
      
      // Try to parse as JSON, fallback to text if that fails
      try {
        return await response.json();
      } catch (e) {
        return await response.text();
      }
    } catch (error) {
      console.error("[API] Fetch error:", error);
      throw error;
    }
  },

  getUserStreams: async (userId) => {
    const qs = new URLSearchParams({ user_id: userId }).toString();
    return API.fetch(`get_stream_subscriptions?${qs}`, { method: "GET" });
  },

  deactivateStreamSubscription: async (userId, streamId) => {
    return API.fetch("deactivate_stream_subscription", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        stream_subscription_id: streamId
      })
    })
  },

  reactivateStreamSubscription: async (userId, streamId) => {
    return API.fetch("reactivate_stream_subscription", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        stream_subscription_id: streamId
      })
    })
  },

  deleteStreamSubscription: async (userId, streamId) => {
    return API.fetch("delete_stream_subscription", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        stream_subscription_id: streamId
      })
    })
  }

};

// Custom Modal component since Modal is not available in @aws-amplify/ui-react v6.11.0
const CustomModal = ({ isOpen, onClose, title, children }) => {
  useEffect(() => {
    // Prevent scrolling on body when modal is open
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }
    
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '20px',
        maxWidth: '90%',
        width: '600px',
        maxHeight: '90vh',
        overflow: 'auto',
        position: 'relative'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '15px' 
        }}>
          <Heading level={4}>{title}</Heading>
          <Button variation="link" onClick={onClose} ariaLabel="Close">
            <FaTimes />
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
};

export default function WingSightMain({ onRegisterNotificationControl }) {
  const [streamInputValue, setStreamInputValue] = useState("");
  const [streamList, setStreamList] = useState(new Set());
  const [customUrlInput, setCustomUrlInput] = useState("");
  const [streamInputType, setStreamInputType] = useState("custom");
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [currentStreamId, setCurrentStreamId] = useState(null);

  const streamListRef = useRef();
  const [audioURL, setAudioURL] = useState(""); // AWS Polly component
  const [visible, setVisible] = useState(false);
  const [notification, setNotification] = useState(null);
  const [intervalId, setIntervalId] = useState(null);

  const [streamHistory, setStreamHistory] = useState({});
  const [frameFrequencyInput, setFrameFrequencyInput] = useState(5);

  const { authStatus } = useAuthenticator();

  useEffect(() => {
    if (authStatus !== 'authenticated') return;        // wait until the user is really signed in

    (async () => {
      try {
        const attributes = await fetchUserAttributes();
        const userId = attributes.sub;

        const saved = await API.getUserStreams(userId);           // ② ask the backend
        const streams = saved?.message?.all_stream_subscriptions ?? [];
        const nonDeletedStreams = streams.filter(sub => !sub.is_deleted);

        setStreamList(new Set(nonDeletedStreams));                             // ③ snapshot into state
      } catch (err) {
        console.error("Could not load existing streams:", err);
      }
    })();
  }, [authStatus]);    // <–– runs once on mount *and* whenever auth status flips to “authenticated”

  // Mock data for history and notifications
  // #TODO: Backend - Fetch available streams from backend API
  const streamOptions = [
    {
      "url": "https://www.facebook.com/watch/?v=1582020282265887",
      "name": "Facebook Test Bird Video"
    },
    {
      "url": "https://www.facebook.com/reel/1106103224584592",
      "name": "Facebook Test Bird Reel"
    }
  ]

  // #TODO: Backend - Fetch user's saved streams on component mount 
  // useEffect(() => {  
  //   fetchStreams();
  // }, []);
 
  const handleStreamInputChange = e => {
    setStreamInputValue(e.target.value);
  }

  const handleCustomUrlChange = e => {
    setCustomUrlInput(e.target.value);
  }

  const handleInputTypeChange = e => {
    setStreamInputType(e.target.value);
  }

  const handleFrameFrequencyChange = e => {
    const value = e.target.value;

    // Ensure the value is a positive number or empty
    if (!isNaN(value) && Number(value) >= 1) {
      const intValue = Math.floor(Number(value))
      setFrameFrequencyInput(intValue);
    }
  }

  const submitLink = async (e) => {
    e.preventDefault();

    let videoUrl = ""

    if(streamInputType === "predefined") {
      if(streamInputValue === "") return;

      videoUrl = streamInputValue;

      // clear input field
      setStreamInputValue("");
    } else {
      if(customUrlInput === "") return;

      videoUrl = customUrlInput;

      // Clear input
      setCustomUrlInput("");
    }

    const frameFetchFrequency = frameFrequencyInput;
    const provideNotification = true;
    const result = await saveStreamToBackend(videoUrl, frameFetchFrequency, provideNotification);

    if (result.success) {
      const newStream = result.data;
      const streams = new Set(streamList);

      streams.add(newStream);
      setStreamList(streams);
    }
  }

  const urlToEmbedUrl = (url, options) => {
    // Simple parsing for demonstration
    let embedUrl = '';
    if(url.includes("youtube.com/watch?v=")) {
      const videoId = url.split("v=")[1].split("&")[0];
      embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1`;
    } else if(url.includes("facebook.com")) {
      // Mock Facebook embed
      embedUrl = `https://www.facebook.com/plugins/video.php?href=${encodeURIComponent(url)}&show_text=0&autoplay=1&mute=1&width=${options.width}&height=${options.height}`;
    } else if(url.includes("twitch.tv")) {
      // Mock Twitch embed
      const channel = url.split("twitch.tv/")[1];
      embedUrl = `https://player.twitch.tv/?channel=${channel}&parent=${window.location.hostname}&autoplay=true&muted=true`;
    }
    // For any other URL, just use it directly (would need proper validation in real implementation)
    return embedUrl; 
  }

  const saveStreamToBackend = async (streamURL, frameFetchFrequency, provideNotification) => {
    const attributes = await fetchUserAttributes();
    const userId = attributes.sub;

    const response = await API.fetch("add_stream", {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        url: streamURL,
        frame_fetch_frequency: frameFetchFrequency,
        user_id: userId,
        provide_notification: provideNotification
      }),
    });

    if (response.status === "created") {
      return { success: true, data: response.message };

    } else if (response.status === "error") {
      const userMessage = response?.message?.error_description || "Invalid request.";
      alert(`Error: ${userMessage}`);
      return { success: false };

    } else {
      alert("Unexpected error occurred.");
      console.error("Unhandled error:", response.message);
      return { success: false };
    }
  };

  const fetchStreamHistory = async (id) => {
    try {
      const user = await fetchUserAttributes();
      const userId = user?.sub || '';

      const response = await API.fetch("get_all_stream_subscription_recognitions", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          stream_subscription_id: id.id
        })
      });

      if (response.status === "fetched") {
        return response.message.all_recognition_entries;
      } else {
        console.error(`Failed to fetch recognition history: ${response.message.error_description}`);
        throw new Error(response.message.error_description);
      }
    } catch (error) {
      console.error("[API] Error fetching recognition history:", error);
      throw error;
    }
  };

  const openHistoryModal = async (stream) => {
    setCurrentStreamId(stream.id);
    setShowHistoryModal(true);

    try {
      const history = await fetchStreamHistory(stream);

      // Update the state with fetched history
      setStreamHistory((prevHistory) => ({
        ...prevHistory,
        [stream.id]: history
      }));
    } catch (error) {
      console.error("Failed to fetch stream history:", error);
    }
  };


  const toggleStream = async (stream) => {
    if (stream.is_active) {
      await deactivateStream(stream);
    } else {
      await reactivateStream(stream);
    }

    setStreamList(prev => {
      const next = new Set(prev);      // shallow‑copy the old Set

      // remove the old object, add back an updated copy
      next.delete(stream);             // Set identifies by object reference
      next.add({ ...stream, is_active: !stream.is_active });

      return next;                     // React sees a brand‑new Set instance
    });
  };

  const deactivateStream = async (streamToDeactivate) => {
    try {
      const user = await fetchUserAttributes();
      const userId = user?.sub || '';
      const streamId = streamToDeactivate.id;
      const response = await API.deactivateStreamSubscription(userId, streamId);

      if(response.status === 'deactivated') {
      } else {
        console.error(`Failed to deactivate stream ${streamId}: ${response.data.message}`);
        alert(`Failed to deactivate stream. Try again later. Error: ${response.data.message}`);
      }

    } catch (error) {
      console.error("[API] Error while deactivating stream subscription: ", error);
    }
  }

  const reactivateStream = async (streamToReactivate) => {
    try {
      const user = await fetchUserAttributes();
      const userId = user?.sub || '';
      const streamId = streamToReactivate.id;
      const response = await API.reactivateStreamSubscription(userId, streamId);

      if(response.status !== 'reactivated') {
        console.error(`Failed to reactivate stream ${streamId}: ${response.data.message}`);
        alert(`Failed to reactivate stream. Try again later. Error: ${response.data.message}`);
      }

    } catch (error) {
      console.error("[API] Error while deactivating stream subscription: ", error);
    }
  }

  const deleteStream = async (streamToDelete) => {
    try {
      const user = await fetchUserAttributes();
      const userId = user?.sub || '';
      const streamId = streamToDelete.id;
      const response = await API.deleteStreamSubscription(userId, streamId);

      if(response.status === 'deleted') {
        const streams = new Set(streamList);
        streams.delete(streamToDelete);
        setStreamList(streams);

      } else {
        console.error(`Failed to deactivate stream ${streamId}: ${response.data.message}`);
        alert(`Failed to delete stream. Try again later. Error: ${response.data.message}`);
      }

    } catch (error) {
      console.error("[API] Error while deactivating stream subscription: ", error);
    }
  }


  const saveNotificationSettings = async (stream_id) => {
    try {
      const apiBase =
        import.meta.env.VITE_API_GATEWAY_URL ||
        import.meta.env.VITE_WINGSIGHT_API_URL;

      const res = await fetch(`${apiBase}/v1/toggle_stream_notification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subscription_id: stream_id })
      });

      if (!res.ok) {
        const err = await res.text();
        console.error("toggle notification error:", err);
        throw new Error(err);
      }

    } catch (e) {
      alert("Failed to update notification: " + e.message);
    }
  };

     useEffect(() => {
      streamListRef.current = streamList;
    }, [streamList]);

     const fetchNotification = async () => {
      const pollyURL =  `${import.meta.env.VITE_API_POLLY}`;    
      const currentStreams = streamListRef.current;
      if (currentStreams.size === 0) {
        return;
      }
      try {
        const response = await fetch(pollyURL, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        });
        const data = await response.json();
        const audioPlayer = document.getElementById('audio-player');    
        if (data.url) {
          setVisible(true);
          setAudioURL(data.url);
          setNotification(data.message);
          audioPlayer.src = data.url;
          try {
            await audioPlayer.play();
          } catch (e) {
            console.error("Autoplay failed:", e);
          }
          setTimeout(() => setVisible(false), 5000);
        }
      } catch (error) {
        console.error("Error: ", error.message);
      }
    };
  
    const startNotifications = () => {
      const id = setInterval(fetchNotification, 6000);
      setIntervalId(id);
    };
  
    const stopNotifications = () => {
      if (intervalId) {
        clearInterval(intervalId);
        setIntervalId(null);
      }
    };
  
    useEffect(() => { // Register control functions for App.jsx
      if (onRegisterNotificationControl) {
        onRegisterNotificationControl({ startNotifications, stopNotifications });
      }
      return () => {
        if (intervalId) clearInterval(intervalId);
      };
    }, [intervalId]);

  return (
    <>
    <div className="card">
      {/* Stream input form with toggle for predefined vs custom */}
      <Flex as="form" direction="column" gap="small" onSubmit={submitLink}>
        <Flex direction="row" justifyContent="space-between">
          <Flex direction="row" gap="medium">
            <Radio
              value="predefined"
              name="inputType"
              label="Select from predefined streams"
              checked={streamInputType === "predefined"}
              onChange={handleInputTypeChange}
            />
            <Radio
              value="custom"
              name="inputType"
              label="Enter custom URL"
              checked={streamInputType === "custom"}
              onChange={handleInputTypeChange}
            />
          </Flex>
          <Flex direction="row" gap="small" alignItems="center">
            <Label htmlFor="frame-fetch">How often should the video be analyzed? (seconds) </Label>
            <Input 
              id="frame-fetch"
              type="number"
              placeholder={5}
              min={1}
              value={frameFrequencyInput}
              onChange={handleFrameFrequencyChange}
              style={{width: "5rem"}}
            />
          </Flex>
        </Flex>
        
        {streamInputType === "predefined" ? (
          <Flex direction="row" gap="small" alignItems="flex-end">
            <SelectField
              label="Pre-defined Stream URL"
              placeholder="Please select a stream"
              textAlign="left"
              onChange={handleStreamInputChange}
              value={streamInputValue}
              width="100%"
            >
              {streamOptions.map((stream, index) => 
              <option 
                key={index} 
                value={stream.url}
                disabled={streamList.has(stream.url)}>
                  {stream.name}
              </option>)}
            </SelectField>
            <Button 
              type="submit"
              colorTheme="success" 
              variation="primary"
              >Add Stream
            </Button>
          </Flex>
        ) : (
          <Flex direction="row" gap="small" alignItems="flex-end">
            <TextField
              label="Custom Stream URL"
              placeholder="Enter URL (YouTube, Facebook, Twitch, etc.)"
              onChange={handleCustomUrlChange}
              value={customUrlInput}
              width="100%"
            />
            <Button 
              type="submit"
              colorTheme="success" 
              variation="primary"
              >Add Stream
            </Button>
          </Flex>
        )}
      </Flex>
    </div>
    <div>
      <audio id="audio-player" style={{ display: 'none' }}>
        <source src={audioURL} type="audio/mpeg" />
        Your browser does not support the audio element.
      </audio>
      {visible && (
        <div className="notification-popup">
          {notification}
        </div>
      )}
    </div>
    <div className="card">
        <Flex id="stream-list" direction="column" gap="medium">
            {
              streamList.size == 0 ? <p>You do not have any streams.</p> : 
              [...streamList].map((stream, index) => (
                <Card key={index} variation="elevated">
                  <Flex direction="column" gap="small">
                    <Flex justifyContent="space-between" alignItems="center">
                      <Heading level={4}>Stream {index}</Heading>
                      <Flex gap="small">
                        <Button
                          variation="link"
                          onClick={() => openHistoryModal(stream)}
                          title="Recognition History"
                        >
                          <FaHistory />
                        </Button>
                        <Button
                            variation="link"
                            onClick={() => toggleStream(stream)}
                            title={stream.is_active ? "Deactivate stream" : "Reactivate stream"}
                        >
                          {stream.is_active ? <FaPause /> : <FaPlay />}
                        </Button>
                        <Button
                            variation="link"
                            colorTheme="error"
                            onClick={() => deleteStream(stream)}
                            title="Delete Stream"
                        >
                          <FaTrash />
                        </Button>
                      </Flex>
                    </Flex>
                    <iframe 
                      width="560" 
                      height="315" 
                      src={urlToEmbedUrl(stream.url, {width: 560, height: 315})}
                      title="Video player" 
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                      referrerPolicy="strict-origin-when-cross-origin" 
                      allowFullScreen>
                    </iframe>
                  </Flex>
                </Card>
              ))
            }
        </Flex>
    </div>

    {/* Recognition History Modal - Using CustomModal instead of Modal */}
    <CustomModal
      isOpen={showHistoryModal}
      onClose={() => setShowHistoryModal(false)}
      title="Recognition History"
    >
      <Card>
        <Heading level={3} textAlign="center">Bird Recognition History</Heading>
        <Text textAlign="center">Stream {currentStreamId !== null ? currentStreamId + 1 : ""}</Text>
        <Divider />
        
        {currentStreamId !== null && streamHistory[currentStreamId] ? (
          streamHistory[currentStreamId].map((entry, index) => (
            <Card key={index} marginBottom="10px">
              <Flex direction="column" gap="small" alignItems="center">
                <Text fontWeight="bold">{entry.recognized_specie_name}</Text>
                <Text color="gray">{new Date(entry.earth_timestamp).toLocaleString()}</Text>
                <img
                  src={entry.presigned_thumbnail_url}
                  alt={entry.recognized_specie_name}
                  style={{ width: "400px", height: "400px", objectFit: "cover", borderRadius: "8px" }}
                />
              </Flex>
            </Card>
          ))
        ) : (
          <Text textAlign="center">No recognition history available for this stream.</Text>
        )}
        
        <Flex justifyContent="center">
          <Button
            onClick={() => setShowHistoryModal(false)}
            marginTop="1rem"
          >
            Close
          </Button>
        </Flex>
      </Card>
    </CustomModal>
    </>
  );
}

