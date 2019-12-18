#!/usr/bin/env python3

import pytest
from typing import NamedTuple
from dataclasses import dataclass


@dataclass
class Packet:
    message_num: int
    data_len: int
    data: bytes
    checksum: bytes


@dataclass
class Ack:
    message_num: int
    nack: bool = False


class Transmitter:

    PACKET_DATA_SIZE = 3

    def __init__(self, payload):
        self.payload = payload
        self.message_counter = 0

    def next_packet(self) -> bytes:
        data_offset = self.message_counter * self.PACKET_DATA_SIZE
        data_to_send = self.payload[
            data_offset : min(data_offset + self.PACKET_DATA_SIZE, len(self.payload))
        ]

        return Packet(
            message_num=self.message_counter % 2,
            data_len=len(data_to_send),
            data=data_to_send,
            checksum=b"correct",
        )

    def done(self) -> bool:
        return self.message_counter * self.PACKET_DATA_SIZE > len(self.payload)

    def receive(self, ack: Ack):
        # TODO: Check correct message number
        if not ack.nack:
            self.message_counter += 1


class Receiver:
    def __init__(self, buffer_size: int = 100):
        self.received_data = [None] * buffer_size
        self.data_offset = 0
        self.last_message_num = 1
        self.last_data_offset = 0

    def receive(self, packet: Packet) -> Ack:
        print(f"Received: {packet}")

        if packet.message_num == self.last_message_num:
            print("Recieved last packet twice")
            self.data_offset = self.last_data_offset

        if packet.data_len != len(packet.data):
            return Ack(packet.message_num, nack=True)

        if packet.checksum != b"correct":
            print("Incorrect checksum, returning nack")
            return Ack(packet.message_num, nack=True)

        self.received_data[
            self.data_offset : self.data_offset + packet.data_len
        ] = packet.data
        self.last_message_num = packet.message_num
        self.last_message_offset = self.data_offset
        self.data_offset += packet.data_len
        return Ack(packet.message_num)

    def get_received_data(self) -> bytes:
        return bytes(self.received_data[: self.data_offset])


def test_blue_sky():
    tx = Transmitter(payload=b"hello world")
    rx = Receiver()

    while not tx.done():
        p = tx.next_packet()
        print(f"Sent: {p}")
        ack = rx.receive(p)
        tx.receive(ack)

    assert rx.get_received_data() == b"hello world"


def test_lost_ack():
    tx = Transmitter(payload=b"hello world")
    rx = Receiver()

    # First packet is good
    p = tx.next_packet()
    _lost_ack = rx.receive(p)

    # Ack never delivered!
    # tx.receive(_lost_ack)

    # The remaining packets (and the retransmissions)
    while not tx.done():
        p = tx.next_packet()
        print(f"Sent: {p}")
        ack = rx.receive(p)
        tx.receive(ack)

    assert rx.get_received_data() == b"hello world"


def test_lost_packet():
    tx = Transmitter(payload=b"hello world")
    rx = Receiver()

    # First packet is good
    p = tx.next_packet()
    ack = rx.receive(p)
    tx.receive(ack)

    # Second packet never delivered
    _lost_packet = tx.next_packet()

    # The remaining packets (and the retransmissions)
    while not tx.done():
        p = tx.next_packet()
        print(f"Sent: {p}")
        ack = rx.receive(p)
        tx.receive(ack)

    assert rx.get_received_data() == b"hello world"


def test_incorrect_checksum():
    tx = Transmitter(payload=b"hello world")
    rx = Receiver()

    # First packet is good
    p = tx.next_packet()
    ack = rx.receive(p)
    tx.receive(ack)

    # Second packet is delivered with an incorrect checksum
    p = tx.next_packet()
    p.checksum = b"incorrect!"
    ack = rx.receive(p)
    tx.receive(ack)

    # The remaining packets (and the retransmissions)
    while not tx.done():
        p = tx.next_packet()
        print(f"Sent: {p}")
        ack = rx.receive(p)
        tx.receive(ack)

    assert rx.get_received_data() == b"hello world"
