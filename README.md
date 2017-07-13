# Team 4 'Guardians of Janelia: An HHMI Group'
## Winners of the Janelia Research Campus 2017 Pixy Battle

The entry point is `lasertag.py`: much of the code is in `utils/`

---

# Pixy Battle

Welcome to the Pixy Battle!

More information can be found on the [official website](http://womenscodingcircle.com/pixyrace/).

## Initial Setup
If you want to return your PixyBot to its default settings, use one of the following methods:

### Method #1: PiBakery

The easiest way to reset your PixyBot is to use one of the PiBakery recipes provided under the ```recipes``` directory.

Download and run [PiBakery](http://www.pibakery.org/) and import the appropriate recipe. You can customize the recipe before flashing your SD card. If you plan to use wifi, you should customize the settings (e.g. fill in the password), but it's best to use an ethernet connection with no wifi (as shown in ```Pixy_Pi_Recipe_NoWifi.xml```) because the install downloads a lot of packages, and it may be slower over wifi.

Insert your PixyBot's SD card into your SD card writer and click "Write". 

Once the card is written, you can insert it back into the PixyBot and boot it up. The install can take up to an hour to download and install all the necessary libraries. If it is interrupted before completion, you can re-run the first boot script like this:

```
$ sudo /boot/PiBakery/firstBoot.sh
```

If you run into any trouble, the ```/boot/PiBakery``` directory also contains logs which can explain what went wrong.

### Method #2: Manual Install

With this alternative method, you will perform the installation steps manually. This has the benefit of being able to check at each step to make sure everything has gone smoothly, as well as being a chance to get familiar with all the dependencies and libraries.

#### Download NOOBS and flash the SD card
Start by [downloading the NOOBS image](https://www.raspberrypi.org/downloads/noobs/) and copying it to the SD card. TO format the SD card, you can use utilities built into your operating system, or download a tool like [SD Formatter](https://www.sdcard.org/downloads/formatter_4/). 

#### Boot
Once the SD card is ready, insert it into the Raspberry Pi, and connect an HDMI cable, a keyboard, and a laptop. Then connect a power cable to boot the Pi. The adapter should be capable of at least 2A @ 5V.

#### Install dependencies 
Open a terminal window and type the following command to download and install the necessary system packages:
```
$ sudo apt-get install git libusb-1.0-0-dev \
    qt4-dev-tools g++ libboost-all-dev cmake swig
```

#### Clone this git repository
```
$ git clone https://github.com/WomensCodingCircle/pixybattle.git
```

#### Run the installer
This will download and build all the required libraries, and install them in the appropriate locations.
```
$ cd pixybattle
$ ./install.sh
```

## Using SSH
We recommend enabling SSH, so that you can connect to the Pi remotely:
1. Enter `sudo raspi-config` in a terminal window
2. Select **Interfacing Options**
3. Navigate to and select **SSH**
4. Choose **Yes**
5. Select **Ok**
6. Choose **Finish**

If you have a Macbook, you can now connect directly to the Pi with an ethernet cable, and then run ssh from Terminal:
```
$ ssh pi@raspberrypi.local
```
Other operating systems require [some extra effort](https://pihw.wordpress.com/guides/direct-network-connection/).

## Using PixyMon
In order to assign color signatures for the PixyCam to recognize, you must use a utility called **PixyMon**. To run this utility, connect an HDMI monitor, keyboard, and mouse to the Raspberry Pi and log into the GUI environment. If you followed all the setup steps above, you should see a shortcut to PixyMon on your desktop. 

## Running the code

Once the initial set up is complete, you should be able to run any of the scripts provided in ```src/python```:

* **racer.py** - this is the basic line-following racer code from 2016's Pixy Race
* **circle.py** - randomly roams about around and pauses for 5 seconds each time it gets hit with an opposing IR gun
* **lasertag.py** - follows Pixy's signature #1 (as set in PixyMon) and tries to fire the IR gun every second

You must run these scripts as root (i.e. using ```sudo```), for example:

```
$ cd ~/pixybattle/src/python
$ sudo python lasertag.py
```

## FAQs

### My PixyBot keeps rebooting, what gives?

This is usually due to power issues. If you are running off batteries, make sure they are not drained. If you have power plugged into the micro USB port, make sure that it is capable of supplying 5V @ 2A. Do __not__ plug the Pi into a regular USB data port.


