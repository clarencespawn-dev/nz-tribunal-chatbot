// Single place to point the frontend at a backend.
// Swap apiBaseUrl when moving from local dev to a deployed Lambda Function URL.
window.CHATBOT_CONFIG = {
  apiBaseUrl: "http://localhost:8000",
  // apiBaseUrl: "https://YOUR-LAMBDA-URL.lambda-url.ap-southeast-2.on.aws",
};
