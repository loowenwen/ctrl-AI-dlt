FROM public.ecr.aws/lambda/python:3.12

# System deps for ffmpeg, yt-dlp, curl, etc.
RUN yum -y install shadow-utils tar gzip && \
    curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
      | tar -xJ && \
    mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg && \
    mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    pip install --no-cache-dir yt-dlp

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Your code
COPY agents/sentiment_agents/ /var/task/
# Ensure lambda_handler.py is at /var/task
COPY lambda_handler.py /var/task/

# Set the handler
CMD ["lambda_handler.handler"]