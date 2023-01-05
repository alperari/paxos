import sys
import os
import random
import threading
from multiprocessing import Process, Barrier
import zmq
import time
import numpy

BASE_PORT = 5550

# MESSAGE FORMAT = "START|CRASH xxx|JOIN:from:to"

# def receiveMessagesAsProposer(proposer_id, numProc):
#     for pid in numProc:


def sendFailure(msg, proposer_id, target_id, prob):
    pass


def broadcastFailure(msg, proposer_id, numProc, prob):
    for target_id in range(numProc):
        # send message to target with pid=pid
        sendFailure(msg, proposer_id, target_id, prob)
        pass

    pass


def customSendMessage(body, sender_id, target_id, push_sockets_dict):
    socket = push_sockets_dict[target_id]

    message = f"{body}:{sender_id}:{target_id}"
    socket.send_string(message)


def customBroadcastMessage(body, sender_id, push_sockets_dict):
    for target_id, socket in push_sockets_dict.items():
        message = f"{body}:{sender_id}:{target_id}"
        socket.send_string(message)


def parseMessage(msg):
    msg = msg.split(":")
    body = msg[0]
    from_id = int(msg[1])
    to_id = int(msg[2])
    return body, from_id, to_id


def PaxosNode(node_id, value, numProc, prob, numRounds):
    maxVotedRound = -1
    maxVotedVal = None
    proposeVal = None
    decision = None

    # Create PULL socket (1 socket) (use bind since it will receive messages from N nodes)
    context = zmq.Context()
    socket_pull = context.socket(zmq.PULL)
    socket_pull.bind(f"tcp://127.0.0.1:{BASE_PORT + node_id}")

    # Create PUSH sockets (N sockets) (use connect since they will be used to send 1 message)
    push_sockets_dict = {}

    for target_id in range(numProc):
        socket_push = context.socket(zmq.PUSH)
        socket_push.connect(f"tcp://127.0.0.1:{BASE_PORT + target_id}")
        push_sockets_dict[target_id] = socket_push

    # Wait for everyone finishing establishing their connections
    time.sleep(1)

    # Run algorithm
    for r in range(numRounds):
        print("node_id:", node_id, "entering round:", r)

        is_proposer = r % numProc == node_id

        if is_proposer:
            time.sleep(0.5)
            print("round:", r, "proposer:", node_id)

            # Is the node crashed with probability 'prob'
            # is_crashed = numpy.random.choice([True, False], p=[prob, 1 - prob])
            is_crashed = False

            print("round:", r, "node_id:", node_id, "is_crashed:", is_crashed)

            if is_crashed:
                # broadcastFailure(f"CRASH {node_id}", node_id, numProc, prob)
                pass
            else:
                # broadcastFailure("START", node_id, numProc, prob)
                customBroadcastMessage("START", node_id, push_sockets_dict)
                pass

        # Receive 'START|CRASH' from proposer
        # TODO
        message_received = socket_pull.recv_string()

        (
            message_received_body,
            message_received_from,
            message_received_to,
        ) = parseMessage(message_received)

        print(
            "node_id:",
            node_id,
            "received message:",
            message_received,
        )

        time.sleep(0.5)

        if message_received_body == "START":

            if is_proposer:
                # Receive response from N-1 acceptors ('JOIN')
                join_count = 1
                print("I am porposer:", node_id, "listening messages")

                for _ in range(numProc - 1):
                    message_received = socket_pull.recv_string()
                    print("proposer received:", message_received)
                    (
                        message_received_body,
                        message_received_from,
                        message_received_to,
                    ) = parseMessage(message_received)

                    if message_received_body == "JOIN":
                        join_count += 1
                
                print("JOIN count:", join_count)

            else:
                time.sleep(0.5)

                if message_received_body == "START":

                    print("node:", node_id, "sending message to proposer")
                    customSendMessage(
                        body="JOIN",
                        sender_id=node_id,
                        target_id=message_received_from,
                        push_sockets_dict=push_sockets_dict,
                    )

    pass


def main(args):
    numProc = int(args[1])
    prob = float(args[2])
    numRounds = int(args[3])

    # Create processes
    # Each process represents a paxos node
    processes = []

    for node_id in range(numProc):
        value = random.randint(0, 1)
        process = Process(
            target=PaxosNode,
            args=(
                node_id,
                value,
                numProc,
                prob,
                numRounds,
            ),
        )
        processes.append(process)

    for process in processes:
        process.start()

    # Wait all paxos nodes to finish rounds
    for process in processes:
        process.join()

    pass


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Invalid command line arguments!")
    else:
        main(args=sys.argv)
