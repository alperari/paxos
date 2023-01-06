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


def sendFailure(body, sender_id, target_id, prob, push_socket):
    is_crashed = numpy.random.choice([True, False], p=[prob, 1 - prob])

    message = {}
    if is_crashed:
        message = {"body": "CRASH", "from": sender_id, "to": target_id}
    else:
        message = {"body": body, "from": sender_id, "to": target_id}

    push_socket.send_json(message)
    print(
        "sender_id:",
        sender_id,
        "sent message to target_id:",
        target_id,
        "a message:",
        message,
    )


def broadcastFailure(body, sender_id, numProc, prob, push_sockets_dict):
    for target_id in range(numProc):
        push_socket = push_sockets_dict[target_id]

        # send message to target
        sendFailure(body, sender_id, target_id, prob, push_socket)


def sendRegular(body, sender_id, target_id, push_socket):
    message = {"body": body, "from": sender_id, "to": target_id}

    push_socket.send_json(message)
    print(
        "sender_id:",
        sender_id,
        "sent message to target_id:",
        target_id,
        "a message:",
        message,
    )


def broadcastRegular(body, sender_id, numProc, push_sockets_dict, am_i_excluded=False):
    for target_id in range(numProc):
        push_socket = push_sockets_dict[target_id]

        if am_i_excluded and target_id == sender_id:
            continue

        # send message to target
        sendRegular(body, sender_id, target_id, push_socket)


def PaxosNode(node_id, value, numProc, prob, numRounds, barrier):
    maxVotedRound = -1  # Proposer & Acceptor
    maxVotedVal = None  # Proposer & Acceptor
    proposeVal = None  # Only Proposer
    decision = None  # Only Proposer

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
            # Broadcast 'START'

            time.sleep(0.5)
            print("round:", r, "proposer:", node_id)

            broadcastFailure(
                body="START",
                sender_id=node_id,
                numProc=numProc,
                prob=prob,
                push_sockets_dict=push_sockets_dict,
            )

        # Receive 'START|CRASH' from proposer
        message_received = socket_pull.recv_json()

        # Parse message received
        message_received_body = message_received["body"]
        message_received_from = message_received["from"]
        message_received_to = message_received["to"]

        print(
            "node_id:",
            node_id,
            "received message:",
            message_received,
        )

        time.sleep(0.5)

        # Phase1 --------------------------------------------------
        join_count = 0
        will_propose = False

        if is_proposer:
            # As a proposer:
            is_received_start = False

            if "START" in message_received_body:
                join_count += 1
                is_received_start = True

            elif "CRASH" in message_received_body:
                # TODO
                pass

            # Receive responses from N-1 acceptors ('JOIN|CRASH')
            print("proposer:", node_id, "listening JOIN messages")

            received_maxVotedRound = -1
            received_maxVotedVal = -1

            for _ in range(numProc - 1):
                message_received = socket_pull.recv_json()
                print("proposer received:", message_received)

                # Parse message received
                message_received_body = message_received["body"]
                message_received_from = message_received["from"]
                message_received_to = message_received["to"]

                if "JOIN" in message_received_body:
                    join_count += 1

                    parsed_join = message_received_body.split(" ")

                    if int(parsed_join[1]) > received_maxVotedVal:
                        # If incoming JOIN's maxVotedVal is bigger than previous
                        # Then update previous with incoming maxVotedVal, round too
                        received_maxVotedRound = int(parsed_join[0])
                        received_maxVotedVal = int(parsed_join[1])

            print("proposer:", node_id, "JOIN count:", join_count)

            # If majority joined
            if join_count > int(numProc / 2):
                # If proposer received 'START' from itself in the beginning
                # And if maxVotedRound is -1, then update proposeVal
                if is_received_start:
                    if maxVotedRound == -1:
                        proposeVal = value
                        maxVotedRound = r

                # If proposer didn't receive 'START' from itself in the beginning,
                # Then set maxVotedRound to the maximum maxVotedRound came from JOINs
                # And set maxVotedVal to the maxixmum maxVotedVal came from JOINs
                else:
                    maxVotedRound = received_maxVotedRound
                    maxVotedVal = received_maxVotedVal
                    proposeVal = maxVotedVal

                will_propose = True

            # If majority didn't join
            else:
                will_propose = False

        elif not is_proposer:
            # As an acceptor:

            if "START" in message_received_body:
                time.sleep(0.5)

                print("acceptor:", node_id, "sending message to proposer")

                # Send "JOIN" to proposer
                sendFailure(
                    body=f"JOIN {maxVotedRound} {maxVotedVal}",
                    sender_id=node_id,
                    target_id=message_received_from,
                    prob=prob,
                    push_socket=push_sockets_dict[message_received_from],
                )

            elif "CRASH" in message_received_body:
                # If an acceptor receives 'CRASH', then it responds with 'CRASH' too
                sendRegular(
                    body=f"CRASH {node_id}",
                    sender_id=node_id,
                    target_id=message_received_from,
                    push_socket=push_sockets_dict[message_received_from],
                )

        barrier.wait()
        # Phase2 --------------------------------------------------

        if is_proposer:
            # As a proposer
            time.sleep(1)

            if will_propose:
                # Broadcast 'PROPOSE'
                print("proposer:", node_id, "broadcasting PROPOSE")
                broadcastFailure(
                    body=f"PROPOSE {proposeVal}",
                    sender_id=node_id,
                    numProc=numProc,
                    prob=prob,
                    push_sockets_dict=push_sockets_dict,
                )
            else:
                # Broadcast 'ROUNDCHANGE'
                print("proposer:", node_id, "broadcasting ROUNDCHANGE")
                broadcastRegular(
                    body="ROUNDCHANGE",
                    sender_id=node_id,
                    numProc=numProc,
                    push_sockets_dict=push_sockets_dict,
                )
                # Go for another round
                # continue

        # Receive 'PROPOSE|CRASH|ROUNDCHANGE' from proposer
        message_received = socket_pull.recv_json()

        # Parse message received
        message_received_body = message_received["body"]
        message_received_from = message_received["from"]
        message_received_to = message_received["to"]

        print(
            "node_id:",
            node_id,
            "received message:",
            message_received,
        )

        if is_proposer:
            # As a proposer
            if will_propose:
                # If proposer has proposed new value, then it will listen N responses
                vote_count = 0
                is_received_propose = False

                if "ROUNDCHANGE" not in message_received_body:
                    if "PROPOSE" in message_received_body:
                        vote_count += 1
                        is_received_propose = True

                    elif "CRASH" in message_received_body:
                        # TODO
                        pass

                    # Receive responses from N-1 acceptors ('JOIN|CRASH')
                    print("proposer:", node_id, "listening VOTE messages")

                    for _ in range(numProc - 1):
                        message_received = socket_pull.recv_json()

                        # Parse message received
                        message_received_body = message_received["body"]
                        message_received_from = message_received["from"]
                        message_received_to = message_received["to"]

                        if "VOTE" in message_received_body:
                            vote_count += 1

                    if is_received_propose:
                        maxVotedRound = r
                        maxVotedVal = proposeVal

                    if vote_count > int(numProc / 2):
                        decision = proposeVal

                    print("vote count", vote_count)
            pass

        elif not is_proposer:
            # As an acceptor
            time.sleep(0.5)

            if "PROPOSE" in message_received_body:
                # send 'VOTE' as an acceptor
                sendFailure(
                    body="VOTE",
                    sender_id=node_id,
                    target_id=message_received_from,
                    prob=prob,
                    push_socket=push_sockets_dict[message_received_from],
                )

            elif "ROUNDCHANGE" in message_received_body:
                pass
            elif "CRASH" in message_received_body:
                # If an acceptor receives 'CRASH', then it responds with 'CRASH' too
                sendRegular(
                    body=f"CRASH {node_id}",
                    sender_id=node_id,
                    target_id=message_received_from,
                    push_socket=push_sockets_dict[message_received_from],
                )

            pass

        barrier.wait()
        # Go for next round
    pass


def main(args):
    numProc = int(args[1])
    prob = float(args[2])
    numRounds = int(args[3])

    barrier = Barrier(numProc)

    # Create processes
    # Each process represents a paxos node
    processes = []

    for node_id in range(numProc):
        value = random.randint(0, 1)
        print("main: created node with node_id:", node_id, "value:", value)
        process = Process(
            target=PaxosNode,
            args=(
                node_id,
                value,
                numProc,
                prob,
                numRounds,
                barrier,
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
