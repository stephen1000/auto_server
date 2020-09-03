sudo mkdir -p /opt/factorio
sudo chown 845:845 /opt/factorio
sudo docker run -d \
    -p 34197:34197/udp \
    -p 27015:27015/tcp \
    -v /opt/factorio:/factorio \
    --name factorio \
    --restart=always \
    factoriotools/factorio
