
module.exports = {
  apps: [
    {
      name: "main_server",
      script: "uvicorn",
      args: "main:app --host 0.0.0.0 --port 5000",
      interpreter: "python3",
      env: {
        NODE_ENV: "production"
      }
    },
    {
      name: "responder_server",
      script: "uvicorn",
      args: "responder_server:app --host 0.0.0.0 --port 3001",
      interpreter: "python3",
      env: {
        NODE_ENV: "production"
      }
    }
  ]
}
