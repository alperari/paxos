import sys
import os
import random
import threading
from multiprocessing import Process, Barrier
import zmq
import time
import numpy

BASE_PORT = 5550

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


def PaxosNode(node_id, value, numProc, prob, numRounds):
    maxVotedRound = -1
    maxVotedVal = None
    proposeVal = None
    decision = None

    # Create PULL socket (1 many)
    context = zmq.Context()
    socket_pull = context.socket(zmq.PULL)
    socket_pull.connect(f"tcp://127.0.0.1:{BASE_PORT + node_id}")

    # Create PUSH sockets (numProc many)
    push_sockets_dict = {}
    for target_id in range(numProc):
        socket_push = context.socket(zmq.PUSH)
        socket_push.connect(f"tcp://127.0.0.1:{BASE_PORT + target_id}")
        push_sockets_dict[target_id] = socket_push

    # Wait for everyone finish establishing their connections
    time.sleep(1)

    # Start rounds
    for r in range(numRounds):
        print("node_id:", node_id, "entering round:", r)

        is_proposer = r % numProc == node_id

        if is_proposer:
            print("round:", r, "im proposer:", node_id)

            # Is the node crashed with probability 'prob'
            is_crashed = numpy.random.choice([True, False], p=[prob, 1 - prob])
            print("round:", r, "node_id:", node_id, "is_crashed:", is_crashed)

            if is_crashed:
                broadcastFailure(f"CRASH {node_id}", node_id, numProc, prob)

            else:
                broadcastFailure("START", node_id, numProc, prob)

            # Receive N many massages
            # TODO

        else:
            pass
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
