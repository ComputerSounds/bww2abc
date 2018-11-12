#!/usr/bin/env python
#
#bwwtoabc: will convert a bww file to a abc file
#Heavily adapted from bww2lilly by Jezra Lickter
#copyright: 2018
#GPL v3

from optparse import OptionParser
import sys,os,re,subprocess
import string;

version = "0.9.0"

#make a print function to handle various version of python
def do_print(string):
    try:
        eval("print "+string)
    except:
        print(string)

#define the class that will convert a bww file to a abc file
class bwwtoabc :
    def __init__(self):
            self.tune_elements = []
            self.comments_list = [];
            self.most_recent_note = 0
            self.in_note_group = False
            self.slur_ties_pending = 0;
            self.slur_tie_back = False
            self.unparsed_time_sig = [];

            # compile a few regex queries
            #make a regex to determine if something is a abc note
            self.regex_abcnote= re.compile("^[abcdefgAGB][0-9]*(/[0-9]*)?")
            #try to determine the time signature
            self.sig_regex = re.compile("([0-9])_([0-9])")
            #a regex to find notes
            self.regex_note_info = re.compile("(?P<note>[A-Z]+)(?P<dir>[l|r]*)_(?P<time>[0-9]{1,2})")
            #a regex to find grace notes
            self.regex_grace_note = re.compile("^([h|l]*[abcdefgt])g$")
            self.regex_doublegracenote = re.compile("^([d|e|f|g|t])([h|l]*[a-g])$")
            #a regex to parse doublings
            self.regex_doubling = re.compile("^db([h|l]*[a-g])")
            #a regex to parse half_doublings
            self.regex_half_doubling = re.compile("^hdb([h|l]*[a-g])")
            #a regex to parse thumb_doublings
            self.regex_thumb_doubling = re.compile("^tdb([h|l]*[a-g])")
            #a regex for finding single strikes
            self.regex_single_strike = re.compile("^str([h|l]*[a-g])")
            #a regex for finding G Grace not, themb and half strikes
            self.regex_strike = re.compile("^([l]?)(g|t|h)*st(2|3)*([h|l]*[a-g])");
            #a regex for finding grips
            self.regex_grip = re.compile("^(grp|ggrp|tgrp|hgrp)((?:ha|hg|la|lg|[b-f])?)")
            self.regex_pele = re.compile("^(l)*([t|h]?)pel([h|l]*[a-g]){0,1}")
            #a regex to find dots
            self.regex_dot = re.compile("^'[h|l]*[a-g]$")
            self.regex_doubledot = re.compile("^''[h|l]*[a-g]")
            #a regex to find sub repeats
            self.regex_sub_repeat = re.compile("^'([0-9]+)")
            #a regex to find note slurs, not slur embellishments
            self.regex_slur = re.compile("\^(?P<note_count>[0-9]+)(?P<end_note>[h|l]*[a-g]*)(?P<start_stop>[s|e]*)")
            #we need a list to ignore
            self.ignore_elements = ("sharpf","sharpc","space","&")
            #create a dictionary of common bww elements and their abc counterparts
            self.transpose_dict = {
                "!"             :" | ",        # Bar sign
                "''!I"          :" :|!\n",     # End part w/Repeat
                "''!It"         :" :|!\n",     # This exists for some reason?
                "!I"            :" |]!\n",     # End of part (no repeat)
                "I!''"          :"|: ",        # Start part w/repeat
                "I!"            :"[| ",        # Start part (no repeat)
                "_'"            :"] ",         # End of repeat bar (could use !rbstop! or !rbend! too?)
                "!t"            :" |!\n",      # Next line
                "'intro"        :"[\"Introduction\"",   # start bis - allowed in abcm2ps
                "'bis"          :"[\"bis\"",   # start bis - allowed in abcm2ps
                "'si"           :"[\"S\"",     # Singling part - allowed in abcm2ps
                "'do"           :"[\"D\"",     # Doubling part - allowed in abcm2ps
                "bis_'"         :"] ",         # end bis
                "thrd"          :"{Gdc}",      # D throw
                "hthrd"         :"{dc}",       # Half D throw
                "hvthrd"        :"{GdGc}",     # Heavy D throw
                "hhvthrd"       :"{dGc}",      # Half Heavy D throw
                "gbr"           :"{gAGAG}",    # G grace note birl
                "brl"           :"{GAG}",      # Birl on A
                "tbrl"          :"{aGAG}",     # Thumb birl
                "tbr"           :"{aAGAG}",     # Thumb birl
                "abr"           :"{AGAG}",     # birl    
                "tar"           :"{GdGe}",     # Taorluath
                "tarb"          :"{GBGe}",     # B Taorluath (from D presumbably)
                "tarbrea"       :"{GdGe}",     # IDK
                "htar"          :"{dGe}",      # Half taor
                "htarla"        :"{dGe}",      # Half taor
                "htarlg"        :"{dGe}",      # Half taor
                "crunl"         :"{GdGeAfA}",  # Crunluath
                "crunlb"        :"{GBGeAfA}",  # B Crunluath
                "hcrunlla"      :"{dAeAfA}",      # Crunluath
                "hcrunllgla"    :"{dGeAfA}",      # Crunluath
                "bubly"         :"{GdGcG}",    # bubly
                "hbubly"        :"{dGcG}",     # half bubly
                "darodo"        :"{GdGcG}",    # Darado
                "darodo16"      :"{G2dGcG2}",  # Darado
                "hdarodo"       :"{dGcG}",     # Half Darado
                "dre"           :"{AfA}",      #
                "edre"          :"{eAfA}",     #
                "edrela"        :"{eAfA}",     # Should enhance edre parsing
                "edreb"         :"{eBfB}",     # Should enhance edre parsing
                "edrec"         :"{ecfc}",     # Should enhance edre parsing
                "edred"         :"{edfd}",     # Should enhance edre parsing
                "godro"         :"{gcGdG}",    # IDK
                "gotro"         :"{gBGdG}",    # IDK
                "otro"          :"{BGdG}",     # IDK
                "gedre"         :"{geAfA}",    #
                "gdare"         :"{gfege}",    #
                "tedre"         :"{aeAfA}",    #
                "tdare"         :"{afege}",    #
                "hedale"        :"{ege}",      #
                "rodin"         :"{GBG}",      #
                "din"           :"{G}",        #
                "embari"        :"{eAfA}",     # E, F, G ,throws
                "endari"        :"{eAfA}",     # E, F, G ,throws
                "chedari"       :"{fegefe}",   # E, F, G ,throws
                "hedari"        :"{egefe}",    # E, F, G ,throws
                "tchechere"     :"{ageae}",    #
                "hchechere"     :"{eae}",      #
                "hiharin"       :"{dAGAG}",    #
                "chedare"       :"{fege}",     #
                "deda"          :"{GdG}",      # idk
                "odro"          :"{cGdG}",     #
                "dili"          :"{ag}",
                "tra"           :"{G2dc}",
                "htra"          :"{dc}",
                "tra8"          :"{G2dc}",
                "cadged"        :"{ge4d}",
                "cadge"         :"{ge4}",
                "caded"         :"{e4d}",
                "cade"          :"{e4}",
                "cadaed"        :"{ae4d}",
                "cadae"         :"{ae4}",
                "fcadged"       :"{gHe4d}",
                "fcadge"        :"{gHe4}",
                "fcaded"        :"{He4d}",
                "fcade"         :"{He4}",
                "fcadaed"       :"{aHe4d}",
                "fcadae"        :"{aHe4}",
                "cadgf"         :"{gf4}",
                "cadaf"         :"{af4}",
                "fcadgf"        :"{gHf4}",
                "fcadaf"        :"{aHf4}",
                "dare"          :"{fege}",     #
                "dbsthg"        :"{gag}",      #
                "dbstf"         :"{fgf}",      #
                "fine"          :"!fine!y",
                "dacapoalfine"  :"!D.C.alfine!y",
                "coda"          :"O",
                "dacapoalcoda"  :"!D.C.alcoda!y",
                "codasection"   :"O",
                "segno"         :"!segno!",
                "dalsegno"      :"!D.S.!",
                }

    def parse_quote(self, comment_element):

            commentType = comment_element.group("type");
            # Get the comment and condense to 1 line
            commentText = comment_element.group("content");
            commentText = commentText.replace("\r"," ")
            commentText = commentText.replace("\n"," ")

            # Saving in tune header info.
            if commentType == "T":
                if self.tune_title:
                    do_print("File contains multiple tunes and should be examined closely.");
                self.tune_title.append(commentText);
            elif commentType == "Y":
                self.tune_type.append(commentText);
            elif commentType == "M":
                self.tune_author.append(commentText);
            elif commentType == "F":
                self.tune_footer.append(commentText);
            
            if commentType == "I" or commentType == "X" and commentText:
                # Put this inline message on the list, put a marker in its palce.
                self.comments_list.append(commentText)
                comment_name = "comment" + str(len(self.comments_list));
                replacementText = comment_name;
            elif commentType == "T":
                # Insert a "header#" part as a placeholder.
                header_name = "header" + str(len(self.tune_title));
                replacementText = header_name;
            else:
                replacementText = "";

            return replacementText;

    def stripNonPrintableCharacters(self, file_text):
            filtered_string = ''.join(filter(lambda x:x in string.printable, file_text));
            if filtered_string != file_text:
                do_print("This file contains non-printable characters which will be ignored.")
            return filtered_string;
    def get_and_strip_metadata(self, file_text):
            #get the title,type,author of the file, these are in quotes
            quote_regex = re.compile("\"(?P<content>.*?)\"(,\((?P<type>[A-Z]).*?\))?", flags=re.S|re.M)
            # tune_info = quote_regex.findall(file_text)

            self.tune_title = []
            self.tune_type = []
            self.tune_author = []
            self.tune_footer = []

            file_text_out = quote_regex.sub(self.parse_quote, file_text);
            
            # If no (or incomplete) metadata, insert some.
            if not self.tune_title:
                self.tune_title.append(self.input_file_name);
                file_text_out = "header1" + file_text_out;

            #try to determine the time signature
            result = self.sig_regex.search(file_text_out)
            if result:
                self.tune_time_sig = result.group(1)+"/"+result.group(2)
                self.unparsed_time_sig = result.group(0);
            else:
                self.tune_time_sig = "C"

            # Strip the "Other junk" up to a close parens.
            sub_rule = r'Bagpipe.*';
            file_text_out = re.sub(sub_rule, "", file_text_out);
            sub_rule = r'^(MIDINoteMappings|FrequencyMappings|InstrumentMappings|GracenoteDurations|FontSizes|TuneFormat)(,.*?\))?';
            # TODO TuneTempo
            file_text_out = re.sub(sub_rule, "", file_text_out, flags=re.S|re.M);
            
            return file_text_out;
    def replaceBadBang(self, matchObj):
            # if this isn't in the dict, try to throw in a space first.
            if matchObj.group(0) not in self.transpose_dict.keys():
                replacement = matchObj.group("bang") + " " + matchObj.group("nextpart");
                do_print("Replacing \"" + matchObj.group(0) + "\" with \"" + replacement + "\" before parse");
            else:
               replacement = matchObj.group(0);
            return replacement;
    def parse(self):
            # create a string that represents the converted contents of the file
            #open the file read only
            file_handle = open(self.original_file,"r")
            #read the contents of the file
            file_text = file_handle.read()

            file_text = self.stripNonPrintableCharacters(file_text);

            file_text = self.get_and_strip_metadata(file_text);

            #get the tunes note info
            #greedy, multiline, from first ampersand to !I or 't (or just the end??)
            notes_regex = re.compile("&.*",re.S)
            result = notes_regex.search(file_text)
            try:
                tune_notes = result.group()
            except:
                #no notes were found, what kind of file is this
                self.quit("No notes were found.\nIs this a valid input file?")
            tune_notes = file_text;
            # look for a bang with something after it that isn't in the dict
            bang_no_space_regex = re.compile("(?<=\s)(?P<bang>!)(?P<nextpart>\S+)");
            tune_notes = bang_no_space_regex.sub(self.replaceBadBang, tune_notes);
                
                

            #replace all whitespace characters with spaces
            tune_notes = tune_notes.replace("\r"," ")
            tune_notes = tune_notes.replace("\n"," ")
            tune_notes = tune_notes.replace("\t"," ")

            #split the string into it's constituents elements
            elements = tune_notes.split()
            for element in elements:
                self.transpose(element)

            if self.slur_ties_pending:
                do_print("Unmatched tie start found.")

    def abcnote(self,bwwname):
            #convert a bww notename to a abc notename
            #make the notename lowercase
            notename = bwwname.lower()

            if notename =="lg":
                abcnote = "G"
            elif notename == "la":
                abcnote ="A"
            elif notename == "hg":
                abcnote = "g"
            elif notename == "ha" or notename =="t":
                abcnote = "a"
            elif notename == 'b':
                abcnote = "B"
            else:
                abcnote = notename
            return abcnote

    def changenotevalue(self,time):
            timeDict = {
            "64":"1/8",
            "32":"1/4",
            "16":"1/2",
            "8" :"1",
            "4" :"2",
            "2" :"4",
            "1" :"8",
            "0" :""
            };
            value = timeDict[time];
            if time == "0":
                do_print("Cannot parse the note with _0. Just using a value of 1.");
            return value;

    def parse_slur(self, slur_result):
            #get the matching elements
            note_count = slur_result.group("note_count")
            end_note = slur_result.group("end_note")
            start_stop = slur_result.group("start_stop");

            # Don't parse until the end of the group.
            if start_stop == "s":
                return;
            
            #get the length of the slur as an integer
            slur_len = int(note_count);
            into_len = "";

            if slur_len > 10:
                into_len = ":" + str(int(slur_len % 10));
                slur_len = int(slur_len / 10);
                

            # find the position of the note that is slur_len from the end
            #get the tune_elements lenght
            elem_index = len(self.tune_elements)-1
            note_count = 0
            while note_count < slur_len:
                element = self.tune_elements[elem_index]
                #is this element a note?
                is_note = self.regex_abcnote.search(element)
                if is_note:
                        #increment the note count
                        note_count+=1
                #decrease the element index
                elem_index-=1

            #add the slur start just after the start note
            self.tune_elements.insert(elem_index+1,"(" + str(slur_len) + into_len)
            # Move the most recent note index.
            self.most_recent_note += 1;
            #add the slur end (just a space to separate);
            self.tune_elements.append(" ")

    def doublenote(self, note):
            doubleDict = {
            "ha": "{ag}",
            "a":  "{ag}",
            "hg": "{gf}",
            "g":  "{gf}",
            "f":  "{gfg}",
            "e":  "{gef}",
            "d":  "{gde}",
            "c":  "{gcd}",
            "b":  "{gBd}",
            "B":  "{gBd}",
            "b":  "{gBd}",
            "A":  "{gAd}",
            "la": "{gAd}",
            "G":  "{gGd}",
            "lg": "{gGd}",
            }
            doubling = doubleDict[note];
            return doubling;
            
    def halfdoublenote(self, note):
            doubleDict = {
            "f":  "{fg}",
            "e":  "{ef}",
            "d":  "{de}",
            "c":  "{cd}",
            "B":  "{Bd}",
            "b":  "{Bd}",
            "A":  "{Ad}",
            "la": "{Ad}",
            "G":  "{Gd}",
            "lg": "{Gd}",
            }
            doubling = doubleDict[note];
            return doubling;
                        
    def thumbdoublenote(self, note):
            doubleDict = {
            "f":  "{afg}",
            "e":  "{aef}",
            "d":  "{ade}",
            "c":  "{acd}",
            "B":  "{aBd}",
            "b":  "{aBd}",
            "A":  "{aAd}",
            "la": "{aAd}",
            "G":  "{aGd}",
            "lg": "{aGd}",
            }
            doubling = doubleDict[note];
            return doubling;
            
    def parsegrip(self, grip_result):
            style = grip_result.group(1);
            note = grip_result.group(2);

            grip = "{";
            # Initial grace note
            if style == "tgrp":
                grip += "a";
            elif style == "ggrp":
                grip += "g";

            # preceding note
            if note:
                grip += self.abcnote(note);

            if note or style != "hgrp":
                grip += "G";

            grip += "dG}";

            # Grip from D (with a B)
            if style == "grp" and note == "b":
                grip = "{GBG}";

            # special cases:
            if note == "f" and style == "ggrp":
                grip = "{gfGfG}";
            if note == "f" and style == "tgrp":
                grip = "{afGfG}";
            if note == "hg" and style == "tgrp":
                grip = "{agGfG}";
            if note == "f" and style == "hgrp":
                grip = "{fGfG}";

            
            return grip;
    
    def parsepele(self, pele_result):
            note = pele_result.group(3);
            style = pele_result.group(2);
            isLight = pele_result.group(1);
            peleDict = {
                "la"  :"{gAeAG}",
                "b"   :"{gBeBG}",
                "c"   :"{gcecG}",
                "d"   :"{gdedG}",
                "e"   :"{gefeA}",
                "f"   :"{gfgfe}"};
            
            peleThumbDict = {
                "la"  :"{aAeAG}",
                "b"   :"{aBeBG}",
                "c"   :"{acecG}",
                "d"   :"{adedG}",
                "e"   :"{aefeA}",
                "f"   :"{afgfe}",
                "hg"  :"{agagf}"};
            peleHalfDict = {
                "la"  :"{AeAG}",
                "b"   :"{BeBG}",
                "c"   :"{cecG}",
                "d"   :"{dedG}",
                "e"   :"{efeA}",
                "f"   :"{fgfe}",
                "hg"  :"{gagf}"};
            peleLightDict = {
                ""    :"{gdedc}",
                "t"   :"{adedc}",
                "h"   :"{dedc}"};
                    
            if style:
                if style == "t":
                    pele = peleThumbDict[note];
                elif style == "h":
                    pele = peleHalfDict[note];
            else:
                pele = peleDict[note]
                
            if isLight:
                pele = peleLightDict[style];

            return pele;
    
    def parsestrike(self, strike_result):
            islight = strike_result.group(1)
            notetype = strike_result.group(2)
            count = strike_result.group(3)
            note = strike_result.group(4)

            strikeDict = {
            "ha": "ag",
            "hg": "gf",
            "g":  "gf",
            "f":  "fe",
            "e":  "eA",
            "d":  "dG",
            "c":  "cG",
            "b":  "BG",
            "la": "AG",
            };
            prefixDict = {
            None  : "{",
            "g" : "{g",
            "h" : "{",
            "t" : "{a",
            };

            strike = strikeDict[note];
            if count == "2":
                strike = strike[-1:] + strike;
            elif count == "3":
                strike = strike[-1:] + strike[-2:] + strike;

            # If this is a double or triple G, thumb or half strike
            # precede with the note.
            if notetype and count:
                strike = self.abcnote(note) + strike;

            strike = prefixDict[notetype] + strike + "}";

            # light strikes.... ugh
            if islight == "l":
                if notetype == "h":
                    strike = "{dc}"
                    if count == "2":
                        strike = "{dcdc}"
                    elif count == "3":
                        strike = "{dcdcdc}"
                elif notetype == "t":
                    strike = "{adc}"
                    if count == "2":
                        strike = "{adcdc}"
                    elif count == "3":
                        strike = "{adcdcdc}"
                elif notetype == "g":
                    strike = "{gdc}"
                    if count == "2":
                        strike = "{gdcdc}"
                    elif count == "3":
                        strike = "{gdcdcdc}"
                else:
                    strike = "{c}"
                    if count == "2":
                        strike = "{cdc}"
                    elif count == "3":
                        strike = "{cdcdc}"

            return strike;
            
    def parsesinglestrike(self, note):
            halfStrikeDict = {
            "hg": "{g}",
            "g":  "{g}",
            "f":  "{f}",
            "e":  "{e}",
            "d":  "{d}",
            "c":  "{c}",
            "B":  "{B}",
            "b":  "{B}",
            "A":  "{A}",
            "la": "{A}",
            "G":  "{G}",
            "lg": "{G}",
            };
            strike = halfStrikeDict[note];
            return strike;

    def dotmostrecentnote(self):
            if self.most_recent_note == 0:
                do_print("This tune starts with a dot which will not be parsed.")
                return;
            #add a dot to the last note
            note = self.tune_elements[self.most_recent_note]

            oldValue = self.get_note_value(note);

            newValue = self.dot_note_value(oldValue);
            self.tune_elements[self.most_recent_note] = \
                self.tune_elements[self.most_recent_note].replace(oldValue,newValue);
            return;
    def doubledotmostrecentnote(self):
            if self.most_recent_note == 0:
                do_print("This tune starts with a double dot which will not be parsed.")
                return
            #add a dot to the last note
            note = self.tune_elements[self.most_recent_note]

            oldValue = self.get_note_value(note);

            newValue = self.doubledot_note_value(oldValue);
            self.tune_elements[self.most_recent_note] = \
                self.tune_elements[self.most_recent_note].replace(oldValue,newValue);
            return;

    def get_note_value(self, note):

            value = re.search(r"[abcdefgAGB]([0-9]+(?:/[0-9]+)?)", note);
            if value:
                return value.group(1);
            else:
                do_print("cant get value of " + note + " Using 1");

    def dot_note_value(self, value):
            valueDict = {
            "1/8": "3/16", # 1/8 + 1/16
            "1/4": "3/8",
            "1/2": "3/4",
            "1"  : "3/2",
            "2"  : "3",
            "3"  : "9/2", # 3 + 3/2 = 6/2 + 3/2 = 9/2
            "4"  : "6",
            "8"  : "12", # 8 + 4
            "16" : "24", # 16 + 8
            "3/2": "9/4", # 3/2 + 3/4 = 6/4 + 3/4
            "3/4": "9/8", # 3/4 + 3/8 = 6/8 + 3/8
            "3/8": "9/16", # 3/8 + 3/16 = 6/16 + 3/16
            }
            newValue = valueDict[value];
            return newValue;

    def doubledot_note_value(self, value):
            valueDict = {
            "1/8": "7/32", # 1/8 + 1/16 + 1/32
            "1/4": "7/16", # 1/4 + 1/8 + 1/16
            "1/2": "7/8",
            "1"  : "7/4",
            "2"  : "7/2",
            "4"  : "7",
            "8"  : "14",
            "16" : "28",   # 16 + 8 + 4
            }
            newValue = valueDict[value];
            return newValue;
    def format_tempo(self, tempoValue):
            fundamental_beat = "1/4"
            if self.unparsed_time_sig == "6_8":
                fundamental_beat = "3/8";
            formattedTempo = "[Q:" + fundamental_beat + "=" + tempoValue + "]"
            return formattedTempo;
                
    def format_header(self, headerNumber):
    
            lpText = "\n\nX:" + str(headerNumber + 1) + "\n";

            # Number of headers define length of this array. No need to check.
            thisTitle = self.tune_title[headerNumber]
            lpText += "T:" + thisTitle + "\n"

            if len(self.tune_type) > headerNumber:
                thisType = self.tune_type[headerNumber]
                lpText += "R:" + thisType + "\n"
            else:
                do_print("This file has more tune titles than tune types");
            
            if len(self.tune_author) > headerNumber:
                thisAuthor = self.tune_author[headerNumber];
                lpText += "C:" + thisAuthor + "\n"
            else:
                do_print("This file has more tune titles than tune composers");
            
            # TODO: put the footer below the tune using %%text 
            # With W: there seems to be a bug where footer is printed in the middle of the tune
            # immediately preceeding any %%text insertion.  That is, %%text is interpreted as the
            # end of the tune.
            if len(self.tune_footer) > headerNumber:
                # Cram the footer in the "W:" field which appears at the bottom.
                thisFooter = self.tune_footer[headerNumber]
                lpText += "W:" + thisFooter + "\n"
            else:
                do_print("This file has more tune titles than tune footers");

            # override beat length for 2/4 time.
            lpText += "L:1/8\n"
            lpText += "K:HP\n"
            lpText += "M:" + self.tune_time_sig + "\n";

            # lptext = "\n\nX:%i\nM:%s\nT:%s\nR:%s\nC:%s\nL:1/8\nW:%s\nK:HP\n" % \
                # (headerNumber + 1, 
                # self.tune_time_sig,
                # thisTitle, 
                # thisType,
                # thisAuthor,
                # thisFooter,
                # )
            return lpText;
    def transpose(self,element):
            #receive a bww element and return a abc equivelent

            #is the element a note?
            note_result = self.regex_note_info.search(element)
            if note_result:
                note = self.abcnote( note_result.group("note") ) \
                    + self.changenotevalue(note_result.group("time"))

                if self.slur_tie_back:
                    self.slur_tie_back=False
                    note = "-" + note;

                if note_result.group("dir") == None or note_result.group("dir") == "":
                    self.tune_elements.insert(self.most_recent_note+1," ");
                elif note_result.group("dir") == "r" and not self.in_note_group:
                    self.in_note_group=True
                    # The next note should be in a group.
                    self.tune_elements.insert(self.most_recent_note+1," ");
                elif note_result.group("dir") == "l":
                    if self.in_note_group:
                        self.in_note_group=False
                
                    
                    
                self.tune_elements.append(note)
                self.most_recent_note = len(self.tune_elements)-1

                return
            #is the element a grace note?
            grace_result=self.regex_grace_note.search(element)
            if grace_result:
                grace = "{"+self.abcnote( grace_result.group(1) )+ "}"
                self.tune_elements.append(grace)
                return
            double_grace_results = self.regex_doublegracenote.search(element);
            if double_grace_results:
                grace = "{" + \
                    self.abcnote(double_grace_results.group(1)) + \
                    self.abcnote(double_grace_results.group(2)) + "}";
                self.tune_elements.append(grace);
                return;
            #is the element a doubling?
            doubling_result=self.regex_doubling.search(element)
            if doubling_result:
                doubling = self.doublenote(self.abcnote( doubling_result.group(1) ))
                self.tune_elements.append(doubling)
                return
            #is the element a half doubling?
            hdoubling_result=self.regex_half_doubling.search(element)
            if hdoubling_result:
                half_doubling = self.halfdoublenote(self.abcnote( hdoubling_result.group(1) ));
                self.tune_elements.append(half_doubling)
                return
            #is the element a thumb doubling?
            tdoubling_result=self.regex_thumb_doubling.search(element)
            if tdoubling_result:
                thumb_doubling = self.thumbdoublenote(self.abcnote( tdoubling_result.group(1) ));
                self.tune_elements.append(thumb_doubling)
                return                
            #is the element a strike?
            single_strike_result=self.regex_single_strike.search(element)
            if single_strike_result:
                strike = self.parsesinglestrike(single_strike_result.group(1));
                self.tune_elements.append(strike);
                return
            strike_result=self.regex_strike.search(element)
            if strike_result:
                strike = self.parsestrike(strike_result);
                self.tune_elements.append(strike);
                return

            grip_result = self.regex_grip.search(element);
            if grip_result:
                grip = self.parsegrip(grip_result);
                self.tune_elements.append(grip);
                return
            pele_result = self.regex_pele.search(element);
            if pele_result:
                pele = self.parsepele(pele_result);
                self.tune_elements.append(pele);
                return;
                
            #is the element a dot?
            dot_result=self.regex_dot.search(element)
            if dot_result:
                self.dotmostrecentnote();
                return
            dot_result=self.regex_doubledot.search(element)
            if dot_result:
                self.doubledotmostrecentnote();
                return

            #is the element a slur?
            slur_result = self.regex_slur.search(element)
            if slur_result:
                self.parse_slur(slur_result);
                return

            #is this a bww tie slur?
            if element == "^ts":
                self.tune_elements.append("(");
                # NEW FORMAT: tie after NEXT note
                self.slur_ties_pending += 1;
                return
            elif element == "^te" and self.slur_ties_pending:
                # Only parse ^te as an ending when we saw a start (^ts) 
                # This maintains compatibility with the old format
                self.slur_ties_pending -= 1;
                self.tune_elements.append(")");
                return;
            elif element.startswith("^t"):
                # OLD FORMAT (e.g. ^tc ^tla, ^te etc.) add tie BEFORE next note.
                self.slur_tie_back = True;
                return;

            if element.startswith("comment"):
                #len comment == 8
                commentNumber = int(element[7:])-1;
                commentToInsert = self.comments_list[commentNumber];
                # See if this comment was on its own line.
                if len(self.tune_elements) and ("\n" in self.tune_elements[-1]):
                    # use a %%text  style comment
                    formattedComment = "%%text " + commentToInsert + "\n"; 
                else:
                    # use a "^text" style comment
                    formattedComment = "\"^" + commentToInsert + "\""; 
                self.tune_elements.append(formattedComment);
                return;

            if element.startswith("header"):
                headerNumber = int(element[6:])-1;
                headerToInsert = self.format_header(headerNumber);
                self.tune_elements.append(headerToInsert);
                return;

            if element.startswith("TuneTempo,"):
                # TODO want to handle tempo changes. For now, let fall into unparsed.
                tempoValue = re.search(r'[0-9]+', element);
                if tempoValue:
                    formattedTempo = self.format_tempo(tempoValue.group(0))
                    self.tune_elements.append(formattedTempo);
                    return;

            #is the element the start of a sub_repeat?
            sub_repeat_result = self.regex_sub_repeat.search(element)
            if sub_repeat_result:
                num_part = sub_repeat_result.group(1);


                if int(num_part) > 10:
                    ending_number = str(int(int(num_part)/10));
                    ending_of = str(int(int(num_part)%10));                    
                    sub_repeat = "[\"" + ending_number + " of " + ending_of + "\" "
                else:
                    sub_repeat = "|" + str(num_part) + " ";

                self.tune_elements.append(sub_repeat)
                return

        
            #is the element in the ignore list?
            if element in self.ignore_elements:
                return

            #if the element is a start double,
            #check if the previous element was a end double
            # if len(self.tune_elements):
            #     last_element = self.tune_elements[-1]
            #     if element=="I!''" and last_element.find(":|"):
            #             #replace the last element with a double double
            #             self.tune_elements[-1] = ":|!\n|: "
            #             return

            #is this a time sig? or Common time or Cut time?
            result = self.sig_regex.search(element)
            if result:
                if result.group(0) != self.unparsed_time_sig:
                    self.tune_time_sig = result.group(1)+"/"+result.group(2);
                    self.tune_elements.append("[M:" + self.tune_time_sig + "]");
                    self.unparsed_time_sig = result.group(0);
                return

            if element == "C" or element == "c":
                if element != self.unparsed_time_sig:
                    self.unparsed_time_sig = element;
                    self.tune_time_sig = "C";
                    self.tune_elements.append("[M:C]");
                return;
            if element == "C_" or element == "c_":
                if element != self.unparsed_time_sig:
                    self.unparsed_time_sig = element;
                    self.tune_time_sig = "C|";
                    self.tune_elements.append("[M:C|]");
                return;

            if element.startswith("fermat"):
                self.tune_elements[-1] = "H" + self.tune_elements[-1]
                return;
            
            if element.startswith("sharp") and not element in ["sharpf", "sharpc"]:
                self.tune_elements.append("#");
                return;            
            if element.startswith("natural"):
                self.tune_elements.append("=");
                return;
            if element.startswith("flat"):
                self.tune_elements.append("_");
                return;
            if element.startswith("echo"):
                echonote = "{" + self.abcnote(element[4:]) + "}";
                self.tune_elements.append(echonote)
                return;

            if element in ["pc", "pcb", "phcla"]:
                # Crunluath 
                self.tune_elements[self.most_recent_note] = "\"_C\"" + self.tune_elements[self.most_recent_note];
                return;

            if element in ["pt", "ptb", "phtla", "ptbrea"]:
                # Toarluath
                self.tune_elements[self.most_recent_note] = "\"_T\"" + self.tune_elements[self.most_recent_note];
                return;
            
            if element in ["pl", "plb", "phlla"]:
                # Lemluath
                self.tune_elements[self.most_recent_note] = "\"_L\"" + self.tune_elements[self.most_recent_note];
                return;

            if element in ["pcmb", "pcmd", "pcmc"]:
                # Crunluath a mach insert reversed c U+0186 - modified NEXT note
                self.tune_elements.append("\"_\\u0186\"");
                return;

            if element in ["ptmb", "ptmc", "ptmd"]:
                # Taorluath a machs Insert an up tack U+22A5 
                self.tune_elements.append("\"_\\u22A5\"");
                return;

            if element in ["pclg"]:
                # Want a sideways C... this is the closest I found
                self.tune_elements[self.most_recent_note] = "\"_\\u1D12\"" + self.tune_elements[self.most_recent_note];
                return;

            if element in ["ptlg"]:
                # right tack - i dont know what this is
                self.tune_elements[self.most_recent_note] = "\"_\\u22A2\"" + self.tune_elements[self.most_recent_note];
                return;

            if element in ["ptriplg", "ptripla", "ptripb", "ptripc"]:
                # G gracenote triplings Insert a triple bar U+22A6A
                self.tune_elements.append("\"_\\u2261\"");
                return;

            if element in ["pembari", "pendari", "phiharin", "pdare", "penbain", "potro", "podro", "pedre"]:
                # add a mordent (squiggle) on NEXT note
                self.tune_elements.append("P");
                return;

            if element in ["padeda"]:
                # add a mordent (squiggle) on PREVIOUS note
                self.tune_elements[self.most_recent_note] = "P" + self.tune_elements[self.most_recent_note];
                return

            if element in ["pdili", "ptra", "phtra", "ptra8", "pgrp"]:
                # add a trill (tr)
                self.tune_elements.append("!trill!");
                return
                
            if element in ["pchedari", "phedari"]:
                self.tune_elements.append("!turn!");
                return;

            if element in ["pdarodo", "pdarodo16", "phdarodo"]:
                # add a turn??? modifies NEXT note
                self.tune_elements.append("!turn!");
                return

            try:
                # Lookup everything else in the dictionary.
                dict_result = self.transpose_dict[element]
                if dict_result:
                    self.tune_elements.append(dict_result)
                    return;
            except:
                do_print( "unparsed: " + element)
                self.tune_elements.append("[r:unparsedBWW " + element + "]");
            return

    #handle writing the output
    def create_output_file(self):
            #determine the output file
            output_file = os.path.join(self.file_dir, self.output_file_name)
            #open the file for writing
            file_handle = open(output_file,"w")
            #write the data to the file
            text = self.get_abc_text()
            file_handle.write(text)
            #close the handle
            file_handle.close()
            #return the string of the path to the file
            return output_file

    def set_file(self, file_path, output):
            #determine the absolute path to the file
            if os.path.isfile(file_path):
                abs_file = file_path;
            else:
                abs_file = os.path.join(os.getcwd(),file_path)
            self.input_file_name = os.path.basename(abs_file)
            (self.output_file_name, ext) = os.path.splitext(self.input_file_name)
            self.output_file_name += ".abc";

            #does the file exist?
            if os.path.isfile(abs_file):
                self.original_file = abs_file
                self.file_dir = os.path.dirname(abs_file)
            else:
                raise Exception(abs_file + " is not a file")
            
            if output:
                potentialPath = os.path.dirname(output);
                if not potentialPath:
                    # just file name. Put it here.
                    self.file_dir = os.getcwd();
                    self.output_file_name = output;
                if os.path.isdir(output):
                    # dir specified
                    self.file_dir = output;
                elif os.path.isdir(potentialPath):
                    # dir + file name
                    self.file_dir = potentialPath;
                    self.output_file_name = os.path.basename(output);
                


    def quit(self,string=""):
            if string!="":
                do_print(string)
            sys.exit()

    def get_abc_text(self):
            tune_text = "".join(self.tune_elements)
            
            # These directives should all work with abcm2ps.
            abcFormattingHeader  = "% File: " + self.input_file_name + "\n"
            abcFormattingHeader += "%%flatbeams     1\n"
            abcFormattingHeader += "%%straightflags 1\n"
            abcFormattingHeader += "%%landscape     1\n"
            abcFormattingHeader += "%%breaklimit    1.0\n"
            abcFormattingHeader += "%%maxshrink     1.0\n"
            abcFormattingHeader += "%%gracespace    6.5 6.5 10.0\n"
            abcFormattingHeader += "%%notespacingfactor 1.0\n"
            abcFormattingHeader += "%%leftmargin    1.0cm\n"
            abcFormattingHeader += "%%rightmargin   1.0cm\n"

            lptext = abcFormattingHeader + tune_text;

            return lptext

#use the bww2abc class
if __name__ == "__main__" :
    parser = OptionParser()
    parser.add_option("-i", "--in", dest="input",
            help="the FILE to convert", metavar="FILE")
    parser.add_option("-o", "--out", dest="output",
            help="the OUTFILE name", metavar="OUTFILE")
    parser.add_option("-v","--version",dest='version',default=False,
            action="store_true",help="print version information and quit")

    #parse the args
    (options, args) = parser.parse_args()
    if options.version:
            do_print( "bwwtoabc: "+version)
            sys.exit()

    if options.input != None:
            converter = bwwtoabc()
            converter.set_file(options.input, options.output)
            converter.parse()
            new_file = converter.create_output_file()
            # Print the output file name.
            # do_print(new_file)
    else:
        parser.print_help()
sys.exit()
