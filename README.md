# mistery_murder_ia
mistery murder diner games with AI

the objective of this project is to demonstrate llm capabilities to generate complex interrelated stories.

Mistery Murder Dinner Games are Agatha Cristie inspired rol games where each person plays a character involved into a murder. The stroy have multiple interrelated characters with differente motives and stories. To provide a interesting game play all characters must have information about the relation of other characters with the victim. Also we must provide means to the players to resolve the murder. 

From the AI perspectiv there are several challenges for generating this rol-game: 
- Logical consistency must be maintained along several prompts. 
- Problem complexity grows with the number of players. 
- Complex information must be transfered between prompts. 

# Chain based solution

First aproach to the problem is using a chain of prompts to create the story. The following prompts are defined: 
- Character Creation 
- Victim Generation
- Motive Generation for each character. 
- Secrets: each character knows a secret of the relation of other character with the victim. 
- Murder circustances: time of murder and murderer selection 
- Alibis: each character is able a to excuplate another character from the murder. The murderer is not excuplated by any alibi. 

# Graph consistency check

To check the consistency of the story LLM are used to create a knowledge graph with all the variableas of the story. this knowledgraph can be represented in a diagram to quick review the story. 

![Example consistency graph](example\graph.png "Example consistency graph")

# Agent based solution

Due to the high complexity of the stories a lot of inconsistencies are found. Those inconsistencies could be solved easily with a manual review but an automatic solution should be made. REACT Agents technology allow the sistem to review the story using the knowledge graph and regenerate the inconsistent parts. 




# running
create env_keys file with this line

```
NVIDIA_API_KEY='nvapi-xxxxxxxxxxxxx'
```





# chars structure
```
chars_final = [ {"name": 
                "short":
                "long_bio": 
                "motive": 
                "secret":
                }]
victim ={"name": 
        "short":
        "long_bio":}

murderer: int
```