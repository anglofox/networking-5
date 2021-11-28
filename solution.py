from socket import *
import os
import sys
import struct
import time
import select
import statistics
import binascii
# Should use stdev

ICMP_ECHO_REQUEST = 8
TIMEOUT_MSG = "Request timed out."


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer



def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return TIMEOUT_MSG

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fill in start

        # Fetch the ICMP header from the IP packet
        ipTtl = recPacket[8:9]
        ttl = struct.unpack("b", ipTtl)[0]
        icmpHeader = recPacket[20:28]
        type, code, checksum, packetId, sequence = struct.unpack("bbHHh", icmpHeader)
        if packetId == ID:
            bytesInData = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInData])[0]
            print("Reply from {}: bytes={} time={} ms TTL={}".format(destAddr, bytesInData, str(round((timeReceived - timeSent) * 1000, 3)), ttl))
            return timeReceived - timeSent


        # Fill in end
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return TIMEOUT_MSG


def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)

    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str


    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")


    # SOCK_RAW is a powerful socket type. For more details:   http://sockraw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF  # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay


def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,  	# the client assumes that either the client's ping or the server's pong is lost
    delayList = list()
    pingCount = 0
    lostCount = 0

    try:
        dest = gethostbyname(host)
        print("Pinging " + dest + " using Python:")
        print("")
        for i in range(0, 4):
            # Send ping requests to a server separated by approximately one second
            delay = doOnePing(dest, timeout)
            pingCount += 1
            time.sleep(1)  # one second

            if delay == TIMEOUT_MSG:
                lostCount += 1
            else:
                delayList.append(delay)
    except gaierror:
        pass

    # Calculate vars values and return them
    packet_min = min(delayList, default=0)
    try:
        packet_avg = statistics.mean(delayList)
    except statistics.StatisticsError:
        packet_avg = 0.0
    packet_max = max(delayList, default=0)
    try:
        stdev_var = statistics.stdev(delayList)
    except statistics.StatisticsError:
        stdev_var = 0.0

    vars = [str(round(packet_min * 1000, 2)), str(round(packet_avg * 1000, 2)),

            str(round(packet_max * 1000, 2)), str(round(stdev_var * 1000, 2))]

    if pingCount:
        print("")
        print("--- " + host + " statistics ---")
        print("{} packets transmitted, {} packets received, {}% packet loss".format(pingCount, pingCount - lostCount, round((lostCount/pingCount) * 100, 2)))
        print("round-trip min/avg/max/stddev = {}/{}/{}/{} ms".format(str(round(packet_min * 1000, 2)), str(round(packet_avg * 1000, 2)), str(round(packet_max * 1000, 2)), str(round(stdev_var * 1000, 2))))

    return vars


if __name__ == '__main__':
    ping("google.co.il")
    ping("No.no.e")
