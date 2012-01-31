import xml.dom.minidom
import xml.dom
import os
import itertools
import copy
import operator


# corpus data
folder = 'alice/'
files = os.listdir(folder)

# maximum lenght of hybrid-grams to be considered
max_lenght_n_gram = 4
# vertical pruning threshold
v_pruning_threshold = float(0.8)

# this dictionary will contain for each hybrid-gram (key) 
# the k-grams in which it compares (items in form of xml_node_lists)
hybrid_gram_to_bases = {}

# a dictionary to save all the hybrid-grams in order
hybrid_grams_freq_dist = {}

def main():
    
    # scanning all file in alice corpus
    for f in files[:2]:
        xmldoc = xml.dom.minidom.parse(folder+f)
        print '===== GENERATING K-GRAMS from file:', f
        
        # build up k-grams with word forms
        k_grams_list = kGramsNodes(xmldoc, max_lenght_n_gram)
        
        # for each k-gram, produce its hybrid_grams
        for kgram in k_grams_list:
            
            k_gram_text = []
            for gram in kgram:
                k_gram_text.append(tokenToText(gram))

            all_hybrid_grams_from_kgram = []
            
            # build up k-grams with lemmas
            lemmas_hybrid_grams = nGramToHybridLemmas(kgram)
            for hybrid_gram in lemmas_hybrid_grams:
                hgram = []
                for gram in hybrid_gram:
                    hgram.append(gram)
                # found a new hybrid-gram, add it to all_hybrid_grams_from_kgram
                if hgram not in all_hybrid_grams_from_kgram: all_hybrid_grams_from_kgram.append(hgram)
            
            
            hybrid_grams = []
            # build up k-grams with POS (keeping at least one word form or lemma)
            for lemmas_hybrid_gram in lemmas_hybrid_grams:
                hybrid_grams = nGramToHybridPOS(kgram,lemmas_hybrid_gram)
                for hybrid_gram in hybrid_grams:
                    hgram = []
                    for gram in hybrid_gram:
                        hgram.append(gram)
                    # found a new hybrid-gram, add it to all_hybrid_grams_from_kgram
                    if hgram not in all_hybrid_grams_from_kgram: all_hybrid_grams_from_kgram.append(hgram)
            
            # add new hybrid-grams to frequency distribution
            hybridFreqDist(all_hybrid_grams_from_kgram)
        
    # hybrid grams sorted by frequency
    printSortedFreq(11)
    old_2 = len(hybrid_grams_freq_dist)
    
    # remove hybrid-grams that have frequency < 5
    for k in hybrid_grams_freq_dist.keys():
        if hybrid_grams_freq_dist[k] < 5:
            del hybrid_grams_freq_dist[k]
    
    old_1 = len(hybrid_grams_freq_dist)
    
    # operate vertical pruning
    vertical_pruning()
    
    # vertically pruned hybrid grams sorted by frequency
    printSortedFreq(11)
    
    print 'hybrid-grams before frequency filtering: ',old_2
    print 'hybrid-grams after frequency filtering, before pruning: ',old_1
    print 'hybrid-grams after pruning: ', len(hybrid_grams_freq_dist)
    
def printSortedFreq(no_less):
    # hybrid grams sorted by frequency
    sorted_hg = sorted(hybrid_grams_freq_dist.iteritems(), key=operator.itemgetter(1), reverse=True)
    for k in sorted_hg:
        print k[0],' : ',k[1]
        if k[1] == no_less:
            print 'omitting hybrid-grams with freq < ',no_less,' from printing'
            break
        
def vertical_pruning():
    print 'start pruning...'
    
    global hybrid_gram_to_bases
    
    # for each hybrid gram, consider the n_grams_node_list (base) 
    # in which it appears to check percentage and (possibly) prune
    for hgram in hybrid_gram_to_bases.keys():
        # how many POS? and in which index are they?
        # I use this data structure to address these questions
        # hgram_pos will contain indexes of POS in hgram k
        hgram_pos_indexes = []
        for gram in hgram:
            if gram[1] == 'POS':
                hgram_pos_indexes.append(hgram.index(gram))
        
        # search what underlie behind pos elements at a given index
        # at each interested hybrid-gram's base
        for pos_index in hgram_pos_indexes:
            pos_words = []
            for base in hybrid_gram_to_bases[hgram]:
                # extract word form from POS
                pos_words.append (tokenToText(base[pos_index]))  
            # check if more than 80% have same word form
            percentage = checkPercentage( pos_words )
            
            if (percentage[0] != False):
                # prune hybrid-gram from main hybrid-grams dictionary
                if hybrid_grams_freq_dist.has_key(hgram):
                    del hybrid_grams_freq_dist[hgram]
    
                 
# given a list, check wether one of its elements
# has frequency in the list > a certain percentage (v_pruning_threshold)
# (I use this method for vertical pruning)
def checkPercentage(l):
    global v_pruning_threshold
    avg = float(0)
    for e in l:
        avg = float(l.count(e))/float(len(l))
        if avg > v_pruning_threshold:
            return [e,avg]
    return [False,avg]

# this method creates a frequency list of hybrid grams
def hybridFreqDist(all_hybrid_grams_from_kgram):
    global hybrid_grams_freq_dist
    for hg in all_hybrid_grams_from_kgram:
        # using tuple since it is immutable and can be a dictionary key
        hg = tuple(hg)
        if hybrid_grams_freq_dist.has_key(hg):
            hybrid_grams_freq_dist[hg] = hybrid_grams_freq_dist[hg]+1
        else: hybrid_grams_freq_dist[hg] = 1
    
     
# This method, given an ngram with mixed wordforms and lemmas 
# (both its ngram_node_list and its string rappresentation)
def nGramToHybridPOS(ngram_nodes_list, hybrid_base):
    
    global hybrid_gram_to_bases
    
    # using deepcopy instead of copy to avoid memory rewriting
    hybrid_base_clone = copy.deepcopy(hybrid_base)

    hybrid_grams = []

    # generates all combinations of it adding POS, 
    #keeping at least one lemma or wordform (thats why range starts from 1)
    for i in range(1,len(ngram_nodes_list)):
        # generate combinations of lenght = i, from ngram_nodes_list:
        for gram in itertools.combinations(ngram_nodes_list, i):
            hybrid_base = copy.deepcopy(hybrid_base_clone)
            for g in gram:
                hybrid_base[ngram_nodes_list.index(g)] = (tokenToPOS(g),'POS')
            
            # bind every hybrid to its bases (useful for vertical pruning)    
            if not hybrid_gram_to_bases.has_key(tuple(hybrid_base)):
                hybrid_gram_to_bases[tuple(hybrid_base)] = []
                hybrid_gram_to_bases[tuple(hybrid_base)].append(ngram_nodes_list)
            else:
                hybrid_gram_to_bases[tuple(hybrid_base)].append(ngram_nodes_list)
            
            # append new hybrid-gram to list to return  
            hybrid_grams.append(hybrid_base)
       
    return hybrid_grams


# given a ngram_nodes_list, this method generates all combinations
# of word forms and lemmas 
def nGramToHybridLemmas(ngram_nodes_list):
    
    hybrid_grams = []

    for i in range(0,len(ngram_nodes_list)):

        # to generate combinations I use itertools.combinations
        # http://docs.python.org/library/itertools.html
        # here I produce all combinations of lenght i,
        # with i = {0 ... |ngram|}
        for gram in itertools.combinations(ngram_nodes_list, i):
            # create ngram base
            # which corresponds on all its (ordered) word forms
            hybrid_gram = []
            for w in ngram_nodes_list:
                hybrid_gram.append((tokenToText(w),'WORD'))
            
            # mute each combination of word forms in lemmas
            for g in gram:
                hybrid_gram[ngram_nodes_list.index(g)] = (tokenToLemma(g),'LEMMA')
            
            # append new hybrid-gram to list to return  
            hybrid_grams.append(hybrid_gram)
            
    return hybrid_grams
            

# This method retrieves all kgrams with k = {1...n} from the xml parse tree. 
# the kgrams are returned in form of node lists
# kgrams are searching *inside* sentences, that means there will not be
# any case of kgram that belongs to more than one single sentence.
def kGramsNodes(xmldoc, n):

    sentences = xmldoc.getElementsByTagName("sentence")
    s_list = []
    # extract sentences
    for s in sentences:
        s_words_nodes = []
        # extract tokens w in sentence s
        for w in s.getElementsByTagName("token"):
            s_words_nodes.append(w)
        s_list.append(s_words_nodes)
    
    # list that will contain k-grams (from 1-gram to n-grams)
    k_grams = []
    
    # for each sentence token_nodes list
    for sentence in s_list:
        # for each lenght k from 1 to n 
        for k in range(2,n):
            # extract k-grams
            i = 0
            while ( i + k < len(sentence) ):
                temp_kgram = []
                # build every single k-gram in sentence
                # and append it to n_gram list
                j = 0
                for j in range(k):
                    # check if the kgram contains a punct,
                    # if yes, do not add it
                    temp_kgram.append(sentence[i+j])
                
                k_grams.append(temp_kgram)
                    
                i = i+1
        
    # filtering out every k-gram that contains punctuation
    to_remove = []
    for kgram in k_grams:
        flag = False
        for gram in kgram:
            if isPunct(gram):
                flag = True
                k_gram_text = []
                for gram in kgram:                    
                    k_gram_text.append(tokenToText(gram))
        if flag:
            to_remove.append(kgram)
    
    # remove k-grams with punctuation
    for node_to_remove in to_remove:
        k_grams.pop(k_grams.index(node_to_remove))
    
    return k_grams 


# method to filter out k-grams with punctuation
# a punctuation token in alice does not have a <tags> element        
def isPunct(node):
    for child in node.childNodes:
        if child.localName == "tags":
            return False
    return True

###    
# methods to retrieve XML elements and their attributes
###
def tokenToText(node):
    for c in node.childNodes:
        if c.localName == "text":
            return c.firstChild.nodeValue
        
def tokenToLemma(node):
    for c in node.childNodes:
        if c.localName == "lemma":
            return c.firstChild.nodeValue

def tokenToPOS(node):
    for c in node.childNodes:
        if c.localName == "tags":
            for tag in c.childNodes:
                if tag.localName == "morpho":
                    return tag.firstChild.nodeValue

# this is the main part of the program
if __name__ == "__main__":
    main()  
