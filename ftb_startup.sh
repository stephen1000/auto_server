# Run in noninteractive mode
export DEBIAN_FRONTEND=noninteractive

# Install the aws CLI
apt -y install python3
apt -y install python-pip --fix-missing
pip install awscli

# Check for world in S3 & restore if found


# Configure Firewall
iptables -I INPUT -p udp --dport 8080 -j ACCEPT
iptables -I INPUT -p tcp --dport 8080 -j ACCEPT
iptables -I INPUT -p udp --dport 25565 -j ACCEPT
iptables -I INPUT -p tcp --dport 25565 -j ACCEPT
iptables -I INPUT -p udp --dport 8123 -j ACCEPT
iptables -I INPUT -p tcp --dport 8123 -j ACCEPT

# Run server
    
docker run \
    -d \
    -p8080:8080 \
    -p25565:25565 \
    -p8123:8123 \
    --name ftb \
    --mount source=ftbvol,target=/opt/minecraft \
    feedthebeast/ftbrevelation:3.1.0_1.12.2

#   feedthebeast/ftbultimatereloaded:1.8.0_1.12.2 \