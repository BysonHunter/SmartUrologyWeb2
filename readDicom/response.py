import json


def responseOutPaths(outputDir):
    jsonFileName = './outputPath.json'

    answer_json = {
        "outputDirPath": outputDir
    }
    with open(jsonFileName, 'w') as json_file:
        json.dump(answer_json, json_file)

    return answer_json
