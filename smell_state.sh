#!/bin/sh

PIN=21

on() {
  echo 'smell on'
  ./gpiocontrol.sh $PIN out 1
}

off() {
  echo 'smell off'
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
    echo "Usage: $0 {on|off}" >&2
    exit 1
    ;;
esac