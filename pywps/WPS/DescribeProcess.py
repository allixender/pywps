"""
WPS DescribeProcess request handler
"""
# Author:	Jachym Cepicky
#        	http://les-ejk.cz
#               jachym at les-ejk dot cz
# Lince: 
# 
# Web Processing Service implementation
# Copyright (C) 2006 Jachym Cepicky
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from Response import Response
import os

class DescribeProcess(Response):
    """
    Parses input request obtained via HTTP POST encoding - should be XML
    file.
    """

    def __init__(self,wps):
        """
        Arguments:
           self
           wps   - parent WPS instance
        """
        Response.__init__(self,wps)

        self.template = self.templateManager.prepare(self.templateFile)

        #
        # HEAD
        #
        self.templateProcessor.set("encoding",
                                    self.wps.getConfigValue("wps","encoding"))
        self.templateProcessor.set("lang",
                                    self.wps.getConfigValue("wps","lang"))
        self.templateProcessor.set("version",
                                    self.wps.getConfigValue("wps","version"))

        #
        # Processes
        #

        self.templateProcessor.set("Processes",self.processesDescription())

        self.response = self.templateProcessor.process(self.template)

        return

    def processesDescription(self):
        """
        Will return Object with processes description
        """

        processesData = []

        for processName in self.processes.__all__:
            # skip process, if not requested or 
            # identifier != "ALL"
            if not processName in self.wps.inputs["identifier"] and \
                self.wps.inputs["identifier"][0].lower() != "all":
                continue

            processData = {}
            try:
                module = __import__(self.processes.__name__, globals(),\
                                    locals(), [processName])

                process = eval("module."+processName+".Process()")

                # process identifier must be == package name 
                if process.identifier != processName:
                    raise ImportError(
                            "Process indentifier \"%s\" != package name \"%s\": File name has to be the same, as the identifier is!" %\
                            (process.identifier, processName))

                processData["processok"] = 1
                processData["identifier"] = process.identifier
                processData["title"] = process.title
                processData["abstract"] = process.abstract
                processData["Metadata"] = 0 #TODO
                processData["Profiles"] = process.profile
                processData["wsdl"] = process.wsdl
                processData["store"] = process.storeSupported
                processData["status"] = process.statusSupported
                processData["version"] = process.version

                processData["Datainputs"] = self.processInputs(process)
                processData["datainputslen"] = len(processData["Datainputs"])

                processData["Dataoutputs"] = self.processOutputs(process)
                processData["dataoutputslen"] = len(processData["Dataoutputs"])

            except Exception, e:
                processData["processok"] = 0
                processData["process"] = processName
                processData["exception"] = e
            processesData.append(processData)
        return processesData

    def processInputs(self,process):
        """
        Will return Object with process inputs
        """

        processInputs = []
        for identifier in process.inputs:
            processInput = {}
            input = process.inputs[identifier]
            processInput["identifier"] = identifier
            processInput["title"] =     input.title
            processInput["abstract"] =  input.abstract
            processInput["minoccurs"] = input.minOccurs
            processInput["maxoccurs"] = input.maxOccurs
            if input.type == "LiteralValue":
                processInput["literalvalue"] = 1
                self.literalValue(input,processInput)
            if input.type == "ComplexValue":
                processInput["complexvalue"] = 1
                self.complexValue(input,processInput)
            if input.type == "BoudningBoxValue":
                processInput["boundingboxvalue"] = 1
                self.bboxValue(input,processInput)
            processInputs.append(processInput)
        return processInputs

    def processOutputs(self,process):
        """
        Will return Object with process output
        """

        processOutputs = []
        for identifier in process.outputs:
            processOutput = {}
            output = process.outputs[identifier]
            processOutput["identifier"] = identifier
            processOutput["title"] =     output.title
            processOutput["abstract"] =  output.abstract
            if output.type == "LiteralValue":
                processOutput["literalvalue"] = 1
                self.literalValue(output,processOutput)
            if output.type == "ComplexValue":
                processOutput["complexvalue"] = 1
                self.complexValue(output,processOutput)
            if output.type == "BoudningBoxValue":
                processOutput["boundingboxvalue"] = 1
                self.bboxValue(output,processOutput)
            processOutputs.append(processOutput)
        return processOutputs
    
    def literalValue(self,inoutput,processInOutput):

        # data types
        dataTypeReference = self.getDataTypeReference(inoutput)
        processInOutput["dataType"] = dataTypeReference["type"]
        processInOutput["dataTypeReference"] = dataTypeReference["reference"]
        
        # UOMs
        if inoutput.uom:
            processInOutput["UOM"] = 1
            processInOutput["defaultUOM"] = inoutput.uom
        if len(inoutput.uoms) > 0:
            supportedUOMS = []
            for uom in inoutput.uoms:
                supportedUOMS.append({"uom":uom})
            processInOutput["supportedUOMS"] = supportedUOMS
            processInOutput["UOM"] = 1

        # allowed values
        # NOTE: only for inputs, but does not matter
        try:
            if "*" in inoutput.values:
                processInOutput["anyvalue"] = 1
            else:
                processInOutput["allowedValueslen"] = 1
                processInOutput["allowedValues"] = []
                for val in inoutput.values:
                    valrecord = {}
                    if type(val) == type([]):
                        valrecord["minMax"] = 1
                        valercord["minimumValue"] = val[0]
                        valercord["maximumValue"] = val[-1]
                        valercord["spacing"] = inoutput.spacing
                    else:
                        valrecord["discrete"] = 1
                        valrecord["value"] = val
        except AttributeError:
            pass

        return

    def complexValue(self,inoutput,processInOutput):

        processInOutput["mimetype"] = inoutput.formats[0]["mimeType"]
        processInOutput["encoding"] = inoutput.formats[0]["encoding"]
        processInOutput["schema"] = inoutput.formats[0]["schema"]

        processInOutput["Formats"] = []
        for format in inoutput.formats:
            processInOutput["Formats"].append({
                                        "mimetype":format["mimeType"],
                                        "encoding":format["encoding"],
                                        "schema":format["schema"]
                                            })
        return

    def bboxValue(self,input,processInput):
        processInput["crs"] = input.crss[0]

        processInput["CRSs"] = inputs.crss

        return 

