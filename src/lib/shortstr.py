import re



def shorten_string_list(strings: list[str], elide_str: str = '…') -> list[str]:
    
    if len(strings) <= 1:
        return strings
        
    # split string into tokens
    number_of_strings = len(strings)
    string_tokens: list[str|tuple[str]] = [[p for p in re.split(r'([ _/\\+~*#.,;-]|\b)',s) if p != ''] for s in strings]
    max_token_count = max(*[len(l) for l in string_tokens])

    def shorten_in_direction(direction: int):
        """ direction: +1 to start at leftmost token, -1 to start at rightmost token"""

        assert direction in [-1, +1], f'Expected direction to be +1 or -1, got {direction}'
        
        string_pointers = [0 if direction==+1 else len(string_tokens[i]) for i in range(number_of_strings)]
    
        def create_dictionary():
            """ Create a dictionary {token: [string_index,...]} of all tokens """
            dictionary = {}
            for i_string in range(number_of_strings):
                pointer = string_pointers[i_string]
                if pointer < 0 or pointer >= len(string_tokens[i_string]):
                    continue  # pointer out of range; ignore

                token = string_tokens[i_string][pointer]
                if isinstance(token, tuple):
                    continue  # already an elided token; ignore
                
                indices: list[int] = dictionary.get(token, list())
                indices.append(i_string)
                dictionary[token] = indices

            return dictionary

        def get_most_frequent_token(dictionary: dict) -> str|None:
            if len(dictionary) < 1:
                return None
            
            elide_token, elide_token_count = None, 0
            for token in dictionary.keys():
                if isinstance(token, tuple):
                    continue  # already an elided token; ignore
                count = len(dictionary[token])
                if count >= 2 and count > elide_token_count:
                    elide_token_count = count
                    elide_token = token
            
            return elide_token
    
        def try_shorten():
            dictionary = create_dictionary()
            if len(dictionary) == 1:  # perfect result: this token can be elided from *all* strings
                for i in range(number_of_strings):
                    pointer = string_pointers[i]
                    if pointer < 0 or pointer >= len(string_tokens[i]):
                        continue  # pointer out of range; ignore
                    
                    # mark as "to elide" by wrapping it into a tuple
                    if not isinstance(string_tokens[i][pointer], tuple):
                        string_tokens[i][pointer] = (string_tokens[i][pointer],)
                    
                    string_pointers[i] += direction  # advance pointer
            
            else:  # ambigous result, need to look deeper
                
                elide_token = get_most_frequent_token(dictionary)
                if elide_token is None:
                    # there is no clear winner; cannot elide
                    for i in range(number_of_strings):
                        string_pointers[i] += direction  # advance pointer
                    return

                for token,indices in dictionary.items():
                    if token == elide_token:
                        continue
                    for i in indices:
                        for offset in range(-2, +3+1):
                            pointer = string_pointers[i] + offset
                            if pointer < 0 or pointer >= len(string_tokens[i]):
                                continue
                            if string_tokens[i][pointer] == elide_token:
                                # found the to-be-elided token also in this string!
                                string_pointers[i] = pointer
                                break
                
                dictionary = create_dictionary()
                if len(dictionary) == 1:  # perfect result: this token can be elided from *all* strings
                    for token,indices in dictionary.items():
                        if token == elide_token:
                            for i in indices:
                                # mark as "to elide" by wrapping it into a tuple
                                if not isinstance(string_tokens[i][string_pointers[i]], tuple):
                                    string_tokens[i][string_pointers[i]] = (string_tokens[i][string_pointers[i]],)
                    
                    for i in range(number_of_strings):
                        string_pointers[i] += direction  # advance pointer
                
                else:  # still ambigous result; give up
                    for i in range(number_of_strings):
                        string_pointers[i] += direction  # advance pointer
    
        for _ in range(max_token_count):
            try_shorten()

    # run the algorithm twice; once forward, once backward
    shorten_in_direction(+1)
    shorten_in_direction(-1)
    
    def tokens_to_str(tokens):
        result = ''
        accu_str = ''
        accu_elide = ''
        
        def flush_accu(is_last=False):
            nonlocal result, accu_str, accu_elide
            is_first = result==''
            if accu_str != '':
                result += accu_str
                accu_str = ''
            if accu_elide != '':
                if len(accu_elide) >= 2:
                    if not (is_first or is_last):  # hide the elide-string if it is at the beginning or end of string
                        result += elide_str
                else:
                    result += accu_elide
                accu_elide = ''
        
        for token in tokens:
            if isinstance(token, tuple):
                # accumulate multiple elisions (tuples), so that no multiple consecutive elision-strings occur
                if accu_str:
                    flush_accu()
                accu_elide += token[0]
            else:
                if accu_elide:
                    flush_accu()
                accu_str += token
        flush_accu(is_last=True)
        
        return result
    
    return [tokens_to_str(tokens) for tokens in string_tokens]
