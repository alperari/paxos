# Introduction

- [Paxos](<https://en.wikipedia.org/wiki/Paxos_(computer_science)>) is a distributed consensus algorithm that allows a group of processes (or nodes) in a network to agree on a single value despite the presence of faults or failures.

- Paxos algorithm ensures that a single value is chosen and that any proposed value is chosen as the final value, only if a majority of processes agree. It also guarantees that if a value is chosen, it will be the same value chosen by any other correct process that starts the Paxos protocol.

> This implementation is Binary Value & Synchronous version of Paxos Consensus.
> Which means all nodes will move together. A multiprocessing barrier will handle that.
> And the proposed value will be binary (0 or 1).

Plus, this Paxos version will satisfy following properties:

1. ✅ **Agreement**: If multiple rounds result in decisions, decided values must be the same.
2. ✅ **Validity**: Any decided value must be one of the values provided by the clients.
3. ❌ **Termination**: All nodes must eventually terminate. (In this implementation, termination will not be guaranteed again since it will allow any number of nodes to fail at anytime.)

## How To Run?

Command line arguments will be:

```bash
python paxos.py <numProc> <prob> <numRounds>
```

`numProc`: Number of nodes in the network
`prob`: Probability of crash of a node
`numRounds`: Number of rounds that paxos will be applied in.

An example:

```
python paxos.py 3 0.1 1
```

### Specs

- This implementation is using python's multiprocessing library to simulate a network of nodes as processes.
- Processes can communicate using [ZMQ](https://zeromq.org/languages/python/) sockets (PULL-PUSH)
- Each process creates N+1 many sockets.
- 1 socket will be PULL socket for receiving any messages coming from other nodes.
- N sockets will be PUSH sockets for broadcasting message in the network.
- Crash of a node is simulated as a node sending _"CRASH"_ message with a probability, instead of a node is literally crashing.
- In each round, the node that satisfies the condition `roundNumber % numProc = nodeID` will be proposer of this round.

An example of ZMQ socket pipelining can be shown as folows:
![image](https://user-images.githubusercontent.com/68128434/214041350-4263ff8f-f4c9-4ea5-8d67-e4474d8666c9.png)

There are 2 phases in this implementation:

1. START-JOIN phase
2. PROPOSE-VOTE phase

### `START-JOIN` Phase

- Proposer of current round will broadcast "START"
- Other nodes will respond "JOIN <maxVotedRound> <maxVotedVal>" with crash probability.
- If joining nodes constitute majority, then proposer will move to PROPOSE-VOTE phase.
- Else, it will broadcast _"ROUNDCHANGE"_. Then everybody will move to the next round and a new proposer will do the same thing.

### `PROPOSE-VOTE` Phase

- If there is a value decided in the end of previous rounds, proposer will propose this value again, by sending _"PROPOSE <max_value_from_previous_rounds"_
- Else, proposer will propose a new value for the first time in the network. It will propose 0 or 1 because of Binary Consensus.
