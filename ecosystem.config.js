
module.exports = {
  apps: [
    {
      name: "main_server",
      script: "uvicorn",
      args: "main:app --host 0.0.0.0 --port 5000",
      interpreter: "python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: "production"
      }
    },
    {
      name: "responder_server",
      script: "uvicorn",
      args: "responder_server:app --host 0.0.0.0 --port 3001",
      interpreter: "python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: "production"
      }
    }
  ]
}
