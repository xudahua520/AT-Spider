FROM python:3.9-slim

# 👇👇👇 新增这两行 👇👇👇
# 设置默认环境变量，防止没传值时报错
ENV APP_VERSION="Docker Latest"

WORKDIR /app

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

# 🌟 端口修改为 8877
EXPOSE 8877

CMD ["python", "main.py"]