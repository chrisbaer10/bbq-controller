#!/usr/bin/python

from pushover import Client

def send_push(message, title):
        Client().send_message(message, title=title)

send_push("Testing successful", "Test")

