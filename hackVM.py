import sys
import os

def stripCommentsAndEmptyLines(lines):
    resultLines = []
    for line in lines:
        # Processing lines
        if (not line.startswith("//")) and line != "":
            resultLines.append(line.split("//")[0])
    return resultLines

compilationUnitFilename = os.path.basename(sys.argv[0]).split('.')[0]

segmentMappings = {
    'local'    : 'LCL',
    'argument' : 'ARG',
    'this'     : 'THIS',
    'that'     : 'THAT',
}

callCount = 0

def getPushCode(line):
    result = []
    cmdSegments  = line.split(' ')
    memoryType   = cmdSegments[1]
    address = cmdSegments[2]
    if memoryType == 'constant':
        result.extend(["@" + address, "D=A"])
        result.extend(["@SP", "A=M", "M=D"])
    elif memoryType in ['local', 'argument', 'this','that']:
        keyword = segmentMappings[memoryType]
        result.extend(['@' + address, 'D=A'])            # Load the offset into the d register
        result.extend(['@' + keyword, 'M=M+D', 'A=M', 'D=M']) # Move the address by this offset and read the value into D
        result.extend(['@SP', 'A=M', 'M=D'])                  # Setting top of the stack memory to value
        result.extend(['@' + address, 'D=A'])            # Loading the offset into the d register
        result.extend(['@' + keyword, 'M=M-D'])               # Subtracting from the given memory register
    elif memoryType == 'temp':
        result.extend(['@' + str(5 + int(address)), 'D=M'])
        result.extend(['@SP', 'A=M', 'M=D'])
    elif memoryType == 'pointer':
        pointerType = ('THIS' if address == '0' else 'THAT')
        result.extend(['@' + pointerType, 'D=M'])
        result.extend(['@SP', 'A=M', 'M=D'])
    elif memoryType == 'static':
        result.extend(['@' + compilationUnitFilename + '.' + address, 'D=M'])
        result.extend(['@SP','A=M', 'M=D'])
    result.extend(['@SP', 'M=M+1']) # Moving the SP up
    return result

def getPopCode(line):
    result = []
    cmdSegments  = line.split(' ')
    memoryType = cmdSegments[1]
    address  = cmdSegments[2]
    # If it's in one of those registers it's simply loaded into corresponding address
    if memoryType in ['local', 'argument', 'this','that']:
        keyword = segmentMappings[memoryType]
        result.extend(['@' + address, 'D=A', '@' + keyword, 'M=M+D'])
        result.extend(['@SP', 'A=M-1', 'D=M'])
        result.extend(['@' + keyword, 'A=M', 'M=D'])
        result.extend(['@' + address, 'D=A', '@' + keyword, 'M=M-D'])
        # Special handling for temp memory
    elif memoryType == 'temp':
        result.extend(['@SP', 'A=M-1', 'D=M'])
        result.extend(['@' + str(5 + int(address)), 'M=D'])
    elif memoryType == 'pointer':
        pointerType = ('THIS' if address == '0' else 'THAT')
        result.extend(['@SP', 'A=M-1', 'D=M'])
        result.extend(['@' + pointerType, 'M=D'])
    elif memoryType == 'static':
        result.extend(['@SP', 'A=M-1', 'D=M'])
        result.extend(['@' + compilationUnitFilename + '.' + address, 'M=D'])
    result.extend(['@SP', 'M=M-1']) # Moving the SP down
    return result

def getOperationCode(cmd):
    result = []
    if cmd in ["add","sub"]:
        operation = ('+' if cmd == 'add' else '-')
        result.extend(['@SP', 'M=M-1', 'A=M', 'D=M'])
        result.extend(['@SP', 'A=M-1', 'M=M' + operation + 'D'])
    elif cmd in ['eq', 'lt', 'gt']:
        mappings = {'eq' : 'JEQ', 'lt' : 'JLT', 'gt' : 'JGT'}
        keyword = mappings[cmd]
        result.extend(['@SP', 'M=M-1', 'A=M', 'D=M'])   # Loading First value from the stack into d
        result.extend(['@SP', 'M=M-1', 'A=M', 'D=M-D']) # Subtracting second value from the first
        result.extend(['@CondLabel.' + str(currentJumpLabel) + ".True"])  # If true jump to to true label
        result.extend(['D;' + keyword])
        result.extend(['@SP', 'A=M', 'M=0'])  # else set the contents of the SP to 0
        result.extend(['@CondLabel.' + str(currentJumpLabel) + ".End", '0;JMP'])
        result.extend(['(CondLabel.' + str(currentJumpLabel) + ".True)"])
        result.extend(['@SP', 'A=M', 'M=-1']) # set the contents SP to all 1
        result.extend(['(CondLabel.' + str(currentJumpLabel) + ".End)"])
        result.extend(['@SP', 'M=M+1']) # Increment the stack pointer (because we have decremented it twice)
        currentJumpLabel += 1
    elif cmd == 'neg':
        result.extend(['@SP', 'A=M-1', 'M=-M'])
    elif cmd in ['and', 'or']:
        operation = ('&' if cmd == 'and' else '|')
        result.extend(['@SP', 'M=M-1', 'A=M', 'D=M'])
        result.extend(['@SP', 'A=M-1', 'M=M'+ operation +'D'])
    elif cmd == 'not':
        result.extend(['@SP', 'A=M-1', 'M=!M'])
    return result

def getCodeForLines(lines):
    global callCount
    result = []

    currentJumpLabel = 0
    for line in lines:
        cmdSegments  = line.split(' ')
        firstSegment = cmdSegments[0]
        result.append('// ' + line)

        if firstSegment == 'push':
            result.extend(getPushCode(line))
        elif firstSegment == 'pop':
            result.extend(getPopCode(line))
        elif firstSegment == 'label':
            labelName = cmdSegments[1]
            result.extend(['(' + labelName + ')'])
        elif firstSegment == 'if-goto':
            labelName = cmdSegments[1]
            result.extend(['@SP', 'A=M-1', 'D=M', '@SP', 'M=M-1'])
            result.extend(['@' + labelName, 'D;JNE'])
        elif firstSegment == 'goto':
            labelName = cmdSegments[1]
            result.extend(['@' + labelName, '0;JMP'])
        elif firstSegment == 'function':
            functionName = cmdSegments[1]
            argCount     = int(cmdSegments[2])
            vmCommands   = ['label ' + functionName]
            # Initializing localArgs
            for i in range(0, argCount):
                vmCommands.extend(['push constant 0', 'pop local ' + str(i)])
            result.extend(getCodeForLines(vmCommands))
        elif firstSegment == 'return':
            result.extend(['@LCL', 'D=M', '@temp1', 'M=D'])                 # endFrame = LCL
            result.extend(['@5', 'D=D-A', 'A=D', 'D=M', '@temp2', 'M=D'])   # retAddr  = *(endFrame - 5)
            result.extend(['@SP', 'A=M-1', 'D=M', '@ARG', 'A=M', 'M=D'])        # *ARG=pop() -- Get the correct pointer
            result.extend(['@ARG', 'D=M+1', '@SP', 'M=D'])               # SP = ARG + 1
            result.extend(['@1', 'D=A', '@temp1', 'A=M-D', 'D=M', '@THAT', 'M=D']) # THAT = *(endFrame - 1)
            result.extend(['@2', 'D=A', '@temp1', 'A=M-D', 'D=M', '@THIS', 'M=D']) # THIS = *(endFrame - 2)
            result.extend(['@3', 'D=A', '@temp1', 'A=M-D', 'D=M', '@ARG', 'M=D'])  # ARG = *(endFrame - 3)
            result.extend(['@4', 'D=A', '@temp1', 'A=M-D', 'D=M', '@LCL', 'M=D'])  # LCL = *(endFrame - 4)
            result.extend(['@temp2', 'A=M', '0;JMP'])
        elif firstSegment == 'call':
            functionName = cmdSegments[1]
            nArgs        = int(cmdSegments[2])
            argDecrement = nArgs + 5
            result.extend(['@return.' + str(callCount), 'D=A', '@SP', 'A=M', 'M=D', '@SP', 'M=M+1']) # push returnAddress
            result.extend(['@LCL', 'A=M', 'D=M', '@SP', 'A=M', 'M=D', '@SP', 'M=M+1'])  # push LCL
            result.extend(['@ARG', 'A=M', 'D=M', '@SP', 'A=M', 'M=D', '@SP', 'M=M+1'])  # push ARG
            result.extend(['@THIS', 'A=M', 'D=M', '@SP', 'A=M', 'M=D', '@SP', 'M=M+1']) # push THIS
            result.extend(['@THAT', 'A=M', 'D=M', '@SP', 'A=M', 'M=D', '@SP', 'M=M+1']) # push THAT
            result.extend(['@' + str(argDecrement), 'D=A', '@SP', 'A=M', 'D=M-D', '@ARG', 'M=D']) # reposition ARG
            result.extend(['@SP', 'A=M', 'D=M', '@LCL', 'M=D']) # reposition LCL
            result.extend(getCodeForLines(['goto ' + functionName]))
            result.extend(['(return. ' + str(callCount) + ')'])
            callCount += 1
        # Arithmetic operations
        else:
            result.extend(getOperationCode(firstSegment))
    return result

def getFileContents(filePath):
    file = open(filePath, 'r')
    fileContents = file.read()
    file.close()
    return fileContents


result = []

filename = sys.argv[1]
if os.path.isfile(filename):
    print filename + " is filename"
    destFilename = filename.split('.')[0] + ".asm"

    file = open(filename, 'r')
    fileContents = file.read()

    lines  = fileContents.split("\n")
    lines  = stripCommentsAndEmptyLines(lines)

    result = getCodeForLines(lines)
    destContents = ('\n').join(result)
    # print destContents
    file = open(destFilename, 'w')
    file.write(destContents)
elif os.path.isdir(filename):
    # List files in dir
    vmFiles     = filter(lambda x: x.endswith(".vm"), os.listdir(filename))
    vmFilesPath = map(lambda x: filename + "\\" + x, vmFiles)

    for filePath in vmFilesPath:
        print "FilePath: " + filePath + " \n"
        print getFileContents(filePath)

    print vmFilesPath
