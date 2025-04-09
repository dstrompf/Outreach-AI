
module.exports = {
  apps: [
    {
      name: "main_server",
      script: "uvicorn",
      args: "main:app --host 0.0.0.0 --port 5000",
      interpreter: "python3",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1"
      },
      error_file: "logs/main-error.log",
      out_file: "logs/main-out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    },
    {
      name: "responder_server",
      script: "uvicorn",
      args: "responder_server:app --host 0.0.0.0 --port 3001",
      interpreter: "python3",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1"
      },
      error_file: "logs/responder-error.log",
      out_file: "logs/responder-out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    }
  ]
}
