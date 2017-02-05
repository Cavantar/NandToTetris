#
import sys

def getBinary(stringValue, padLength):
    intValue     = int(stringValue)
    resultString = ""
    # Getting the value
    while(intValue > 0):
       resultString = chr(ord('0') + (intValue % 2)) + resultString
       intValue /= 2
    # Padding string
    while(len(resultString) < padLength):
        resultString = '0' + resultString
    return resultString

destBits = {
    'null' : "000",
    'M'    : "001",
    'D'    : "010",
    'MD'   : "011",
    'A'    : "100",
    'AM'   : "101",
    'AD'   : "110",
    'AMD'  : "111"
}

compBits = {
    '0'   : '0101010',
    '1'   : '0111111',
    '-1'  : '0111010',
    'D'   : '0001100',
    'A'   : '0110000',
    '!D'  : '0001101',
    '!A'  : '0110001',
    '-D'  : '0001111',
    '-A'  : '0110011',
    'D+1' : '0011111',
    'A+1' : '0110111',
    'D-1' : '0001110',
    'A-1' : '0110010',
    'D+A' : '0000010',
    'D-A' : '0010011',
    'A-D' : '0000111',
    'D&A' : '0000000',
    'D|A' : '0010101',

    'M'   : '1110000',
    '!M'  : '1110001',
    '-M'  : '1110011',
    'M+1' : '1110111',

    'M-1' : '1110010',
    'D+M' : '1000010',
    'D-M' : '1010011',
    'M-D' : '1000111',
    'D&M' : '1000000',
    'D|M' : '1010101'
}

jumpBits = {
    'null' : '000',
    'JGT'  : '001',
    'JEQ'  : '010',
    'JGE'  : '011',
    'JLT'  : '100',
    'JNE'  : '101',
    'JLE'  : '110',
    'JMP'  : '111'
}

def getDest(instruction):
    result = ""
    splitted = instruction.split('=')
    if len(splitted) > 1:
        result = splitted[0]
    else:
        result = "null"
    return result

def getComp(instruction):
    currentString = instruction
    if('=' in instruction):
        currentString = currentString.split('=')[1]

    if(';' in instruction):
        currentString = currentString.split(';')[0]

    return currentString

def getJump(instruction):
    result = ""
    splitted = instruction.split(';')
    if len(splitted) > 1:
        result = splitted[1]
    else:
        result = "null"
    return result

def stripCommentsAndEmptyLines(lines):
    resultLines = []

    for line in lines:
        # Processing lines
        lineP = line.strip().replace(" ", "")
        if (not lineP.startswith("//")) and lineP != "":
            resultLines.append(lineP.split("//")[0])
    return resultLines

# Starting main program
if len(sys.argv) < 2:
    print "Supply filename of the file to be compiled"
    sys.exit()

filename = sys.argv[1]
destFilename = filename.split(".")[0] + ".hack"

file = open(filename, 'r')
fileContents = file.read()

result = [];
lines  = fileContents.split("\n")
lines  = stripCommentsAndEmptyLines(lines)

symbolTable = {
    'R0'  : 0,  'R1'  : 1,  'R2'  : 2, 'R3'   : 3,
    'R4'  : 4,  'R5'  : 5,  'R6'  : 6, 'R7'   : 7,
    'R8'  : 8,  'R9'  : 9,  'R10' : 10, 'R11' : 11,
    'R12' : 12, 'R13' : 13, 'R14' : 14, 'R15' : 15,
    'SCREEN' : 16384, 'KBD' : 24576,
    'SP' : 0, 'LCL' : 1, 'ARG' : 2, 'THIS' : 3, 'THAT' : 4
}

print ("\n").join(lines)

# First Pass
currentInstruction = 0
lines1 = []

for line in lines:
    if line[0] !='(':
        lines1.append(line)
        currentInstruction += 1
    else:
        symbolName = line[1:].split(")")[0]
        symbolTable[symbolName] = currentInstruction
        print "symbol: " + symbolName + " \t index: " + str(currentInstruction)

lines=lines1
print ("\n").join(lines)

currentSymbolIndex = 16

# Doing second pass
for line in lines:
    lineResult = ""
    # Checking command type
    if line[0] == '@':
        # A command
        # Check if it's a symbol
        stringValue = line[1:]
        if(stringValue.isdigit()):
            lineResult = '0' + getBinary(stringValue, 15)
        else:
            if not (stringValue in symbolTable):
                symbolTable[stringValue] = currentSymbolIndex
                currentSymbolIndex += 1
            lineResult = '0' + getBinary(symbolTable[stringValue], 15)
    else:
        # C command
        dest = getDest(line)
        comp = getComp(line)
        jump = getJump(line);

        lineResult = "111" + compBits[comp] + destBits[dest] + jumpBits[jump]
    print line + "\t" + lineResult
    result.append(lineResult)

file = open(destFilename, 'w')
destFileContents = ("\n").join(result)
print destFileContents

file.write(destFileContents)
