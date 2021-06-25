import sys
import mysql.connector
import random
import threading
from operator import sub
import time
from datetime import datetime 

temperature_fuzzy_set = ['Cool', 'Warm', 'Hot'] # input value degree celcius
soil_fuzzy_set = ['Dry', 'Moist', 'Wet'] # input value PAW of soil_moist
light_fuzzy_set = ['Dark', 'Normal', 'Bright'] #input value sunlight (Lux)

sprinkler_duration_fuzzy_set = ['Short', 'Medium', 'Long'] # output, how long we have to sprinkler our plant ?

read_duration = 10.0   
default_update = 30.0
global dur
dur = 0

def main():
    
    #-----Run main() every 10s-----#
    t = threading.Timer(read_duration, main)
    t.start()

    #----Read inferences rules file -----#
    rules = parse_kb_file('rule.kb')

    over_time = check_time()
    weather_chg, random_temp, random_soil, random_light = check_data()

    #----Determine the categories of inputs-----#
    tmp = temperatureFunction(random_temp)
    soil = soilFunction(random_soil)
    li = lightFunction(random_light)

    # print("")
    # print('Output Of Fuzzyfication')
    # print(tmp)
    # print(soil)
    # print(li)
    # print('')

    inf = inferred(tmp, soil, li,  rules) # inference Process
    # print(inf)
    # print("")

    #---------Mamdani method (first take min, then max)------------#
    result_rule_min = []

    for dt in inf:         #warm            #value                                  #dry        #value
        #print("Temp: ", dt[0][0][0][1], dt[0][0][0][2], ",\t", "Soil_moist: ", dt[0][0][1][1], dt[0][0][1][2], ",\t", "Light: ", dt[0][0][2][1], dt[0][0][2][2],  ",\t","Water_duration: " ,dt[1]) 
        minimum = min(dt[0][0][0][2], dt[0][0][1][2], dt[0][0][2][2])
        result_rule_min.append([dt[1],minimum])   #array                                #dt[1] is the rule/output water duration (short/medium/long)
    #print('')                                                                           #possible rules 


    #print(result_rule_min)

    result_rule_max = {}    #object
    for data in result_rule_min:
        if data[0] in result_rule_max:                      # insert data[0] = long/medium/short into result_rule_max[]
            result_rule_max[data[0]].add(data[1])
        else:
            result_rule_max[data[0]] = set([data[1]])

    output_inference = []
    for key, value in result_rule_max.items():
        output_inference.append([key,max(value)])

    # print('')
    # print('Output Inference is', output_inference)
    # print('')

    #print('Defuzzification')

    #-----AI------#

    
    #-----IF check == true, weather sudden change / time_reach== calculate new water duratoin suggestion every 30 min----#
    if over_time or weather_chg:
        defuzzification(output_inference)
    else:
        pass


    time.sleep(1)
    print("\n")
 #----Read sensor data every 10 sec & Calculate weather threshold-----#
def check_data():
    conn = mysql.connector.connect(user='caini', password='',host='127.0.0.1',database='smart_durian')

    cursor = conn.cursor()

    #----Temperature Input------#
    cursor.execute("SELECT temperature FROM sensor ORDER BY id DESC LIMIT 1")   #use the latest data sort by latest id
    temperature = cursor.fetchone()

    cursor.execute("SELECT temperature FROM sensor ORDER BY id DESC LIMIT 1,1")   #get the second latest data to find threshold
    temperature2 = cursor.fetchone()

    # print("Temperature: ", temperature)
    # print("Second Last Temperature: ", temperature2)

    t_thres = tuple(map(sub, temperature, temperature2))
    temp_threshold = tuple(map(abs, t_thres))  
    print("Temp_threshold", "%.1f" % temp_threshold)
        
    randT = random.randrange(len(temperature)) 
    rand_temp = temperature[randT]

    #------Soil Input----#
    cursor.execute("SELECT soil_moist FROM sensor ORDER BY id DESC LIMIT 1")
    soil_moist = cursor.fetchone()

    cursor.execute("SELECT soil_moist FROM sensor ORDER BY id DESC LIMIT 1,1")
    soil_moist2 = cursor.fetchone()

    s_thres = tuple(map(sub, soil_moist, soil_moist2))
    soil_threshold = tuple(map(abs, s_thres))
    print("Soil_threshold:", "%.1f" % soil_threshold)

    randS = random.randrange(len(soil_moist)) 
    rand_soil = soil_moist[randS]

    #------Light Intensity Input------#
    cursor.execute("SELECT light_intensity FROM sensor ORDER BY id DESC LIMIT 1")
    light = cursor.fetchone()

    cursor.execute("SELECT light_intensity FROM sensor ORDER BY id DESC LIMIT 1,1")
    light2 = cursor.fetchone()

    l_thres = tuple(map(sub, light, light2))        #----Subtract second last with the latest data
    light_threshold = tuple(map(abs, l_thres))
    print("Light_threshold: ", "%.1f" % light_threshold)

    randL = random.randrange(len(light)) 
    rand_light = light[randL]

    t_Thres = tuple(range(1, 7))
    s_Thres = tuple(range(1, 11))
    l_Thres = tuple(range(1, 101))

    if temp_threshold < t_Thres or soil_threshold < s_Thres or light_threshold < l_Thres:
       weather_chg = False
    else:
        weather_chg = True

    return weather_chg, rand_temp, rand_soil, rand_light

    
#---Check time ald reached 30 mins or not----#
def check_time():
    global dur
    dur += 1

    if (dur-1) % (default_update/read_duration) == 0:   #
        print('[INFO] 30 seconds reached')
        return True
    else:
        return False

    
def defuzzification(input):

    result = float(0)

    x1_short = 0
    x2_short = 28
    coefisien_short = float(0)

    x1_medium = 20
    x2_medium = 48
    coefisien_medium = float(0)

    x1_long = 40
    x2_long = 90
    coefisien_long = float(0)

    _short_numerator = float(0)    #pembilang
    _medium_numerator = float(0) #pembilang
    _long_numerator = float(0) #pembilang

    _short_denominator = float(0) #penyebut
    _medium_denominator = float(0) #penyebut
    _long_denominator = float(0) #penyebut

    for data in input:         #input == output inference
        if data[0] == 'Short':
            coefisien_short = data[1]               #assign short probability(0.6xxxx) as coefisien_short
        if data[0] == 'Medium':
            coefisien_medium = data[1]
        if data[0] == 'Long':
            coefisien_long = data[1]

    #--------Between Short & Medium---------------------------

    if coefisien_short != float(0) and coefisien_medium != float(0) and coefisien_long == float(0):     #Value of coefisien short & medium not equal to 0
        x_start_short = x1_short     # == 0
        x_end_short = x1_medium + 1 # should be plus 1,    ==21    (0 - 20)

        x_start_medium = x2_short       #20
        x_end_medium = x1_long + 1 # should be plus 1      == 49   (20 - 48)

        for i in range(x_start_short, x_end_short):                        
            _short_numerator += i * coefisien_short                   
            _short_denominator += coefisien_short
        #     print(_short_numerator)
        #     print(_short_denominator)
        # print('')

        for i in range(x_start_medium, x_end_medium):
            _medium_numerator += i * coefisien_medium
            _medium_denominator += coefisien_medium
            # print(_medium_numerator)
            # print(_medium_denominator)

        result = (_medium_numerator + _short_numerator) / (_medium_denominator + _short_denominator)

        #--------Between Long & Medium---------------------------

    if coefisien_short == float(0) and coefisien_medium != float(0) and coefisien_long != float(0):

        x_start_medium = x2_short
        x_end_medium = x1_long + 1  # should be plus 1

        x_start_long = x2_medium
        x_end_long = x2_long + 1  # should be plus 1

        for i in range(x_start_medium, x_end_medium):
            _medium_numerator += i * coefisien_medium
            _medium_denominator += coefisien_medium

        for i in range(x_start_long, x_end_long):
            _long_numerator += i * coefisien_long
            _long_denominator += coefisien_long

        result = (_medium_numerator + _long_numerator) / (_medium_denominator + _long_denominator)

           #--------Between Short, Medium & Long ---------------------------

    if coefisien_short != float(0) and coefisien_medium != float(0) and coefisien_long != float(0):

        x_start_short = x1_short
        x_end_short = x1_medium + 1  # should be plus 1

        x_start_medium = x2_short
        x_end_medium = x1_long + 1  # should be plus 1

        x_start_long = x2_medium
        x_end_long = x2_long + 1  # should be plus 1

        for i in range(x_start_short, x_end_short):
            _short_numerator += i * coefisien_short
            _short_denominator += coefisien_short

        for i in range(x_start_medium, x_end_medium):
            _medium_numerator += i * coefisien_medium
            _medium_denominator += coefisien_medium

        for i in range(x_start_long, x_end_long):
            _long_numerator += i * coefisien_long
            _long_denominator += coefisien_long

        result = (_short_numerator + _medium_numerator + _long_numerator) / (_short_numerator + _medium_denominator + _long_denominator)

        #--------Short---------------------------

    if coefisien_short != float(0) and coefisien_medium == float(0) and coefisien_long == float(0):
        x_start_short = x1_short
        x_end_short = x1_medium + 1  # should be plus 1

        for i in range(x_start_short, x_end_short):
            _short_numerator += i * coefisien_short
            _short_denominator += coefisien_short

        result = (_short_numerator) / (_short_denominator)

        #--------Medium---------------------------

    if coefisien_short == float(0) and coefisien_medium != float(0) and coefisien_long == float(0):
        x_start_medium = x2_short
        x_end_medium = x1_long + 1  # should be plus 1

        for i in range(x_start_medium, x_end_medium):
            _medium_numerator += i * coefisien_medium
            _medium_denominator += coefisien_medium

        result = (_medium_numerator) / (_medium_denominator)

    #--------Long---------------------------

    if coefisien_short == float(0) and coefisien_medium == float(0) and coefisien_long != float(0):
        x_start_long = x2_medium
        x_end_long = x2_long + 1  # should be plus 1

        for i in range(x_start_long, x_end_long):
            _long_numerator += i * coefisien_long
            _long_denominator += coefisien_long

        result = (_long_numerator)/(_long_denominator)


    finalValue = result  

    hours = int(finalValue) // 60           #divide minutes to hr & min
    minutes = int(finalValue) % 60

    if hours == 0:
       print(minutes, ' Mins\t')
    else:
        print(hours, ' Hrs\t',minutes, ' Mins\t')

    #----INSERT water duration into database (result table)-----#
    # cursor.execute("INSERT INTO result (water_duration) VALUES ('%s')"%(finalValue))
    # conn.commit()



#=========Fuzzy Inference System==============#
def inferred(fuzzification_temp, fuzzification_soil, fuzzification_li, fuzzyfication_rule):
    agenda = []
    possibility = []

    for dt in fuzzification_temp:                       #dt = table data
        agenda.append(dt)                               #insert fuzzification of temp, soil and light into agenda array
    for dt in fuzzification_soil:
        agenda.append(dt)
    for dt in fuzzification_li:
        agenda.append(dt)

    while agenda:
        item = agenda.pop(0)
        for rule in fuzzyfication_rule:
            for j, premise in enumerate(rule[0]):                               #premise = rule[j] in rule.kb
                if premise == item[0]:                                          #if the inference output calculated in temperatureFunctions == the rule[j], then TRUE
                    rule[0][j] = [True, rule[0][j], item[1]]                    #for example, item[0] is cool, moist, then match with rule[4] = medium
            if check_hypothesis(rule[0]):                                          #item[1] is the probability of the category
                conclusion = rule[1]                                            #item[0] == Cool/warm/hot
                possibility.append(rule)
                agenda.append(conclusion)
                rule[0] = [rule[0],'processed']

    return possibility

def check_hypothesis(hypothesis):
    for entry in hypothesis:
        if entry[0] != True:
            return False
    return True


#========Fuzzification=========#
def temperatureFunction(input):           #Determine which category are the input of temperature, show possibility of both category(membership functions)
    linguistik_temperature = []

    if input >= 0 and input <=25:
        linguistik_temperature.append(temperature_fuzzy_set[0]) #Cool
    if input >= 20 and input <=30:
        linguistik_temperature.append(temperature_fuzzy_set[1]) #Warm
    if input >= 25 and input <=40:
        linguistik_temperature.append(temperature_fuzzy_set[2]) #Hot

    #======Use Trapeziodal Function: (x-y)/n=========#

    value_temp = []

    if len(linguistik_temperature) > 1:
        if linguistik_temperature[0] == temperature_fuzzy_set[0] and linguistik_temperature[1] == temperature_fuzzy_set[1]: # Between Cool and Warm
            #Cool
            cool = -(input - 25) / (25 - 20)                    #input is less than 25, so need put - if not the ans will come out negative.
            value_temp.append([linguistik_temperature[0],cool])
            #Warm
            warm = (input - 20) / (25 - 20)
            value_temp.append([linguistik_temperature[1], warm])

        elif linguistik_temperature[0] == temperature_fuzzy_set[1] and linguistik_temperature[1] == temperature_fuzzy_set[2]: # Between Warm and hot
            #Warm
            warm = -(input - 30) / (30-25)
            value_temp.append([linguistik_temperature[0],warm])
            #Hot
            hot = (input - 25) / (30-25)
            value_temp.append([linguistik_temperature[1],hot])
        
    else:
        value_temp.append([linguistik_temperature[0],1])


    return value_temp

def soilFunction(input):                              ##Determine which category are the input of soil_moist
    linguistik_soil = []
    if input >=0 and input <=450:
        linguistik_soil.append(soil_fuzzy_set[0]) # Wet
    if input >=400 and input <=750:
        linguistik_soil.append(soil_fuzzy_set[1]) # Moist
    if input >=700 and input <=1023:
        linguistik_soil.append(soil_fuzzy_set[2]) # Dry

    #==========================
    value_soil = []
    if len(linguistik_soil)>1:
        if linguistik_soil[0] == soil_fuzzy_set[0] and linguistik_soil[1] == soil_fuzzy_set[1] : #Between Wet and Moist
            #Wet
            wet = -(input - 450) / (450 - 400)
            value_soil.append([linguistik_soil[0],wet])
            #Moist
            moist = (input - 400) / (450 - 400)
            value_soil.append([linguistik_soil[1],moist])
        elif linguistik_soil[0] == soil_fuzzy_set[1] and linguistik_soil[1] == soil_fuzzy_set[2] : #Between Moist and Dry
            #Moist
            moist = -(input - 750) / (750 - 700)
            value_soil.append([linguistik_soil[0],moist])
            #dry
            dry = (input - 700) / (750 - 700)
            value_soil.append([linguistik_soil[1],dry])
    else:
        value_soil.append([linguistik_soil[0],1])

    return value_soil

def lightFunction(input):                                ##Determine which category are the input of light
    linguistik_light = []
    if input >=0 and input <=8500:
        linguistik_light.append(light_fuzzy_set[0]) # Dark
    if input >=8000 and input <=15500:
        linguistik_light.append(light_fuzzy_set[1]) # Normal
    if input >=15000 and input <=20000:
        linguistik_light.append(light_fuzzy_set[2]) # Bright

    #==========================
    value_li = []
    if len(linguistik_light)>1:
        if linguistik_light[0] == light_fuzzy_set[0] and linguistik_light[1] == light_fuzzy_set[1] : #Between Dark and Normal
            #Dark
            dark = -(input - 8500) / (8500 - 8000)
            value_li.append([linguistik_light[0],dark])
            #Normal
            normal = (input - 8000) / (8500 - 8000)
            value_li.append([linguistik_light[1],normal])

        elif linguistik_light[0] == light_fuzzy_set[1] and linguistik_light[1] == light_fuzzy_set[2] : #Between Normal and Bright
            #Normal
            normal = -(input - 15500) / (15500 - 15000)
            value_li.append([linguistik_light[0],normal])
            #Bright
            bright = (input - 15000) / (15500 - 15000)
            value_li.append([linguistik_light[1],bright])
    else:
        value_li.append([linguistik_light[0],1])

    return value_li


def parse_kb_file(filename):
    kb_file = open(filename)        # 'rU' is smart about line-endings
    kb_rules = []                         # to hold the list of rules

    for line in kb_file:                  # read the non-commented lines
        if not line.startswith('#') and line != '\n':
            kb_rules.append(split_and_build_literals(line.strip()))

    kb_file.close()
    return kb_rules

def split_and_build_literals(line):
    rules = []
    # Split the line of literals
    literals = line.split(' ')
    hypothesis = []
    while len(literals) > 1:
        hypothesis.append(literals.pop(0))
    rules.append(hypothesis)
    rules.append(literals.pop(0))
    return rules


if __name__ == '__main__':
    main()
    print("\n")

    
