"""
Smart Ticketing System dApp Contract
============================================

Author: Asif Raza
Email: asif@kisti.re.kr

Date: May 16 2018

This code demonstrates use of tickets reservation for events

Deployment in neo-python:

import contract tickets.py 0710 05 False False

"""


from boa.interop.Neo.Runtime import GetTrigger, CheckWitness, Notify, Serialize, Deserialize
from boa.interop.Neo.TriggerType import Application, Verification
from boa.interop.System.ExecutionEngine import GetExecutingScriptHash, GetCallingScriptHash
from boa.interop.Neo.Blockchain import GetHeight, GetHeader
from boa.interop.Neo.Header import GetTimestamp, GetHash, GetNextConsensus
from boa.interop.Neo.App import RegisterAppCall


#owner's wallet script hash
OWNER = b"'z\x99W\x86\x089\xd4=\xe97\xd2\xf0T\xd7\xa4`\xf2\xe7_"

#MCT private net script hash
MCT_SCRIPTHASH = b'\x8dKL\x14V4\x17\xc6\x91\x91\xe0\x8b\xe0\xb8m\xdc\xb4\xbc\x86\xc1'

# MCT App Call in privatenet
MCTContract = RegisterAppCall('c186bcb4dc6db8e08be09191c6173456144c4b8d', 'operation', 'args')

def Main(operation, args):

    trigger = GetTrigger()

    if trigger == Verification():
        if CheckWitness(OWNER):
            return True

        return False

    elif trigger == Application():

        if operation == 'deploy':

            if not len(args) == 3:
                return False

            eventName = args[0]
            startTime = args[1]
            totalNumOfTickets = args[2]
            eventInfo = [eventName, startTime, totalNumOfTickets]

            return deploy(OWNER, eventInfo)
        
        if operation == 'addTickets':

            if not len(args) == 3:
                return False

            ticketsType = args[0]
            ticketPrice = args[1]
            numOfTickets = args[2]
            ticketsSold = 0
            ticketsInfo = [ticketsType, ticketPrice, numOfTickets, ticketsSold]

            return addTickets(OWNER, ticketsInfo)

        if operation == 'verifyTickets':

            if not len(args) == 2:
                return False

            senderAddr = args[0]
            ticketHash = args[1]

            return verifyIdentity(senderAddr, ticketHash)


        if operation == 'checkTicketsLeft':
            Log("In getLeftTickets")
            if not len(args) == 1:
                return False

            ticketType = args[0]

            return getLeftTickets(ticketType)

        if operation == 'checkMyTicket':
            Log("check my Tickets status")
            if not len(args) == 2:
                return False

            senderAddr = args[0]
            ticketType = args[1]            

            return getTicket(senderAddr, ticketType)

        if operation == 'getTicketsInfo':
            Log("In getTicketsInfo")

            return getTickets()

        if operation == 'useMyTicket':
            Log("In useMyTickets")
            if not len(args) == 2:
                return False

            senderAddr = args[0]
            ticketType = args[1]

            return useTicket(senderAddr, ticketType)

        if operation == 'userWithdraw':
            if len(args) != 2:
                print('withdraw amount not specified')
                return False

            t_amount = args[1] * 100000000
            userWallet = args[0]
            myhash = GetExecutingScriptHash()
            Log("myhash log:")
            Log(myhash)

            return MCTContract('transfer', [myhash, userWallet, t_amount])

        if operation == 'ownerWithdraw':
            if not CheckWitness(OWNER):
                print('only the contract owner can withdraw MCT from the contract')
                return False

            if len(args) != 1:
                print('withdraw amount not specified')
                return False
         
            t_amount = args[0] * 100000000
            myhash = GetExecutingScriptHash()

            return MCTContract('transfer', [myhash, OWNER, t_amount])

        # end of normal invocations, reject any non-MCT invocations

        caller = GetCallingScriptHash()

        if caller != MCT_SCRIPTHASH:
            print('token type not accepted by this contract')
            return False

        if operation == 'onTokenTransfer':
            print('onTokenTransfer() called')
            return handle_token_received(caller, args)

    return False


def handle_token_received(chash, args):

    arglen = len(args)

    if arglen < 3:
        print('arg length incorrect')
        return False

    t_from = args[0]
    t_to = args[1]
    t_amount = args[2] * 100000000

    if arglen >= 4:
       op_arg = args[3]  # extra argument passed by transfer()

    if len(t_from) != 20:
        return False

    if len(t_to) != 20:
        return False

    myhash = GetExecutingScriptHash()

    if t_to != myhash:
        return False

    if t_from == OWNER:
        # topping up contract token balance, just return True to allow
        return True

    if op_arg == 'buyTickets':

        if not arglen == 7:
            return False

        ticketType = args[4]
        ticketsQuantity = args[5]
        ticketHash = args[6]

        if not onlyBefore(OWNER):
            Log("Event time not started yet!")
            return False

        amount = compute_price(ticketType, ticketsQuantity)

        return perform_exchange(t_from, t_amount, amount, ticketType, ticketsQuantity, ticketHash)
 
    else:
        print('received MCT tokens!')
        totalsent = Get(t_from)
        totalsent = totalsent + t_amount
        if Put(t_from, totalsent):
            return True
        print('staked storage call failed')
        return False


# Staked storage appcalls

def Get(key):
    return MCTContract('Get', [key])

def Delete(key, value):
    return MCTContract('Delete', [key]) 

def Put(key, value):
    return MCTContract('Put', [key, value])



# supportive functions


#deployment of event information, event Name, event start time and event total number of tickets

def deploy(eventOwner, eventInfo):

    if not CheckWitness(eventOwner):
        print("Must be owner to deploy")
        return False

    if not Get(eventOwner):
        # do deploy logic
        save = Serialize(eventInfo)
        Put(eventOwner, save)
        return True

    return False


#add different types of ticket of an event; e.g. simple, vip, vvip, etc
def addTickets(eventOwner, ticketsInfo):

    if not CheckWitness(eventOwner):
        print("Must be owner to deploy")
        return False

    if not Get('allTickets_key'):
        save =[]
        save.append(ticketsInfo)
        to_save = Serialize(save)
        Put('allTickets_key', to_save)
        return True

    to_retrive = Get('allTickets_key')
    deserialized = Deserialize(to_retrive)
    deserialized.append(ticketsInfo)
    to_save = Serialize(deserialized)
    Put('allTickets_key', to_save)
    return True


#Individuals purchased tickets verification process
def verifyIdentity(senderAddr, ticketHash):

    if not Get(senderAddr):
        Log("verify senderAddr not found return False")
        return False

    to_retrive = Get(senderAddr)

    if to_retrive == ticketHash:
        Log('Address verified!')
        return True

    Log("verify identity final False")
    return False


#get the total number of ticket available at this time 
def getLeftTickets(ticketType):

    if not Get('allTickets_key'):
        Log("tickets Information not found")
        return False


    Log("getLeftTickets functions")
    to_retrive = Get('allTickets_key')
    deserialized = Deserialize(to_retrive)

    if not deserialized[ticketType]:
        return False

    result = deserialized[ticketType][2] - deserialized[ticketType][3]
    return result


#check ticket information of a customer
def getTicket(senderAddr, ticketType):

    if not Get('allTickets_key'):
        Log("tickets Information not found")
        return False


    Log("getTicket function")
    to_retrive = Get('allTickets_key')
    deserialized = Deserialize(to_retrive)

    if not deserialized[ticketType]:
        return False

    senderHash = sha256(concat (deserialized[ticketType][0], senderAddr))

    if not Get(senderHash):
        return False

    retrive_me = Get(senderHash)
    deserial = Deserialize(retrive_me)

    return deserial


#retrive all tickets information
def getTickets():

    if not Get('allTickets_key'):
        Log("tickets Information not found")
        return False

    Log("getTickets function for all tickets")
    to_retrive = Get('allTickets_key')
    deserialized = Deserialize(to_retrive)
    Log("after deserialized")
    descriptions = []
    ticketPrice = []
    ticketsLeft = []
    totalTickets = []
    Log("before for loop")

    for i in deserialized:
        Log("inside for loop")
        descriptions.append(i[0])
        ticketPrice.append(i[1])
        totalTickets.append(i[2])
        ticketsLeft.append(i[2]-i[3])

    Log("before return")
    return (descriptions, ticketPrice, totalTickets, ticketsLeft)



#use the customer's ticket for event attendance
def useTicket(sender, _type):

    if not Get('allTickets_key'):
        Log("tickets Information not found")
        return False


    to_retrive = Get('allTickets_key')
    deserialized = Deserialize(to_retrive)

    if not deserialized[_type]:
        return False

    senderHash = sha256(concat (deserialized[_type][0], sender))

    if not Get(senderHash):
        return False

    retrive_me = Get(senderHash)
    deserial = Deserialize(retrive_me)

    if deserial[0] == 0:
        return False

    elif deserial[1]:
        return False

    else:
        deserial[1] = True
        to_save = Serialize(deserial)
        Put(senderHash, to_save)
        Log("Ticket used")
        return True


#Check the time and date of event started or not
def onlyBefore(eventOwner):

    if not Get(eventOwner):
        return False

    # do deploy logic
    to_retrive = Get(eventOwner)
    deserialized = Deserialize(to_retrive)
    triggerTime = deserialized[1]
    currentHeight = GetHeight()
    currentBlock = GetHeader(currentHeight)
    now_ish = currentBlock.Timestamp

    Log(now_ish)
    Log(triggerTime)
    if now_ish > triggerTime:
        Log("Return true in time check")
        return True

    return False


#calculate total price of required tokens
def compute_price(_type, _numTickets):

    to_retrive = Get('allTickets_key')
    Log('after Get command: number of tickets required')
    (_numTickets)
    deserialized = Deserialize(to_retrive)
    Log('After deserialized')
    unitPrice = deserialized[_type][1] * _numTickets
    Log('after unitPrice')
    Log(unitPrice)
    return (unitPrice)


#check MCT amount is as per total calculated price
def can_exchange(attachments, amount, verify_only):

    Log("can exchnage")
    Log(attachments)
    Log("amount:")
    Log(amount)
    if (attachments/100000000) < amount:
        Log("sent MCT lower than amount")
        return False

    Log("Can exchange return True")
    return True


#ticket exchange
def perform_exchange(t_from, t_amount, amount, ticketType, ticketsQuantity, ticketHash):


#    attachments = get_asset_attachments()  # [receiver, sender, neo, gas]


    Log("t_from")
    Log(t_from)
    Log("t_amount")
    Log(t_amount)
    Log("amount")
    Log(amount)
    Log("ticketType")
    Log(ticketType)
    Log("Quantity")
    Log(ticketsQuantity)
    Log("ticketHash")
    Log(ticketHash)


    exchange_ok = can_exchange(t_amount, amount, False)

    if not exchange_ok:

#       if attachments[2] > 0:
#           OnRefund(attachments[1], attachments[2])

        Log("exchange not ok")
        return False

    to_retrive = Get('allTickets_key')
    deserialized = Deserialize(to_retrive)

    reqTickets = deserialized[ticketType][3] + ticketsQuantity
    availableTickets = deserialized[ticketType][2]

    if reqTickets > availableTickets:
        Log("Requested numbers of ticket not available.")
        return False

    _type = deserialized[ticketType][0]
    sender = t_from
    senderHash = sha256(concat(_type, sender))
    Log("senderHash")
    Log(senderHash)
    Put(sender, ticketHash)
    deserialized[ticketType][3] = deserialized[ticketType][3] + ticketsQuantity

    if not Get('ownerIncome'):
        Put('ownerIncome', amount)
    else:
        income = Get('ownerIncome')
        income = income + amount
        Put('ownerIncome', income)

    if not Get(senderHash):
        saveData = []
        saveData.append(ticketsQuantity)
        saveData.append(False)
        save_me = Serialize(saveData)
        Put(senderHash,save_me)

    else:
        retrive_me = Get(senderHash)
        deserial = Deserialize(retrive_me)
        deserial[0] = deserial[0] + ticketsQuantity
        deserial[1] = False
        save_me = Serialize(deserial)
        Put(senderHash, save_me)

    to_save = Serialize(deserialized)
    Put('allTickets_key', to_save)
#   TicketPayed(sender, amount, ticketsQuantity)
    Log("perform exchnage return True")
    return True
                                




