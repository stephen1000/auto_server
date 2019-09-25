# Notes

-p<External>:<Internal> 
    to forward ports
-it
    dunno yet
-v <foldername>
    to bind docker volumes w/ system volumes (persistant storage)
    
- Docker cares about the order in which you specify arguments vs options, but it won't tell you that

* Future addition: some sort of aliasing for images? Should be able to say "/start <name> to ensure the container named <name> is running, but also should be able to name new containers- for instance, /create <name>:minecraft/ftb-revelation/3.1.0
    * would also need command ala /list <game> <type> <version>
