---
layout: post
title: Raspberry Pi Configs For First Deploy
description: Raspberry Pi Configs For First Deploy
summary: Raspberry Pi Configs For First Deploy
tags: raspberry config deploy
minute: 60
---

first navigate to boot directory on sd card

# for starting ssh service automaticly
```
touch ssh
```

# for connecting wifi automaticly
```
# add these configs on file named wpa_supplicant.conf
country=US # Your 2-digit country code
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
network={
    ssid="YOUR_NETWORK_NAME"
    psk="YOUR_PASSWORD"
    key_mgmt=WPA-PSK
}
```