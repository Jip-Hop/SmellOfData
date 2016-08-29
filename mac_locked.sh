#!/bin/sh

PIN=18

on() {
	echo 'MAC Locked'
	./gpiocontrol.sh $PIN out 1
}

off() {
	echo 'MAC unlocked'
	./gpiocontrol.sh $PIN out 0
}

case "$1" in
	on)
		on
	;;
	off)
		off
	;;
	*)
		echo 'Use: "$0 on|off". Turns on/off the MAC-Locked GPIO Output (normally lights White LED, if LEDs enabled by uC' >&2
		exit 1
	;;
esac
exit 0
