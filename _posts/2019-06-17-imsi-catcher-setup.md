---
layout: post
title: IMSI Catcher Setup
description: These processes were tried with HackRF One device on Ubuntu 19.04
summary: These processes were tried with HackRF One device on Ubuntu 19.04
tags: gsm rf
minute: 5
---

# enrty
These processes were tried with HackRF One device on Ubuntu 19.04 version and `it is used only for educational purposes.`

<img align="center" src="https://raw.githubusercontent.com/x3beche/x3beche.github.io/master/assets/img/1_aFkPd05HtGx1o-CPwfE8NA.png">

&nbsp;
&nbsp;
&nbsp;

# setup


`sudo apt-get update && sudo apt-get upgrade -y`

`sudo apt install gr-gsm gqrx-sdr python-numpy python-scipy python-scapy`

`git clone https://github.com/Oros42/IMSI-catcher.git`


&nbsp;
&nbsp;

# operating
First of all, we need to find gsm frequencies. We run grgsm_scanner on the terminal.

`grgsm_scanner`

<img align="center" src="https://raw.githubusercontent.com/x3beche/x3beche.github.io/master/assets/img/1_DeoPkvdm5jIWZi6jIxGYdg.png">

We found the frequencies. Then we run the program.

`sudo python simple_IMSI-catcher.py - sniff`

Now it's time to listen to the frequency and pull the data. We are opening another terminal. We run grgsm_livemon and connect to the one with the highest PWR value among the frequencies found by grgsm_scanner. I will connect to the frequency of 959.6M

`sudo grgsm_livemon -f 959.6M`

<img align="center" src="https://raw.githubusercontent.com/x3beche/x3beche.github.io/master/assets/img/1_e5abX3KwbPJtPQcnpVibow.png">

<img align="center" src="https://raw.githubusercontent.com/x3beche/x3beche.github.io/master/assets/img/1_qwsILoMR_5KH8uK7PfKx4Q.png">

Yes, It works. Data started to come. Then we look at the other terminal we opened. IMSI Catcher is running.

`Resources : https://github.com/Oros42/IMSI-catcher ,https://osmocom.org/`
