# ChatGPT Team Auto Invite

一个轻量级的 ChatGPT Team 席位自动邀请工具，支持 Docker 一键部署。

### Docker Compose

1. 编辑 `.env` 文件，填入 JWT Token：

```env
JWT_TOKEN=eyJhbGciOi...
```

2. 启动服务：

```bash
git clone https://github.com/Futureppo/team-auto-invite
cd team-auto-invite
docker compose up -d
```


### Docker

```bash
git clone https://github.com/Futureppo/team-auto-invite
cd team-auto-invite
docker build -t team-auto-invite .
docker run -d -p 8080:8080 --env-file .env team-auto-invite
```

## License

AGPLv3
