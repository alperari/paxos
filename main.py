import sys
import os
import random
import threading
from multiprocessing import Process, Value, Array
import zmq
import time


def sendFailure(msg, proposerId, targetId, prob):
    pass


def broadcastFailure(msg, proposerId, numProc, prob):
    for targetId in range(numProc):
        # send message to target with pid=pid
        sendFailure(msg, proposerId, targetId, prob)
        pass

    pass


def PaxosNode(node_id, value, numProc, prob, numRounds):
    maxVotedRound = -1
    maxVotedVal = None
    proposeVal = None
    decision = None

    for r in range(numRounds):
        is_proposer = r % numProc == node_id

        if is_proposer:
            print("round:", r, "im proposer:", node_id)
            # Broadcast 'START'
            broadcastFailure("START", node_id, numProc, prob)

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
