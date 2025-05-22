import type { Window as WindowInterface } from "../interface";
import ChatBox from "./ChatBox/ChatBox";
import { motion } from "framer-motion";
import ToolBox from "./ToolBox/ToolBox";

export default function Window({index=0, items, firstWindow=true}: {index?: number, items: WindowInterface[], firstWindow?: boolean}) {

  const toRender = (window: WindowInterface) => {
    switch (window.windowType) {
      case "chatbox" : 
        return <ChatBox sendData={window.props.sendData}/>
      case "toolbox" :
        return <ToolBox messages={window.props.messages}></ToolBox>
    }
  }

  const [first, ... rest] = items

  if(index % 4 == 0) {
    return <div className="w-full h-full flex-1 min-h-0 min-w-0 flex flex-row">
      {
        rest.length > 0 && <Window index={index+1} items={rest} firstWindow={false}></Window>
      }
      <motion.div
      initial={firstWindow ? false : { height: 0 }}
      animate={{height: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      key={first.id}
      className="w-full h-full flex-1 min-h-0 min-w-0 border border-l-2 border-secondary">
        {toRender(first)}
      </motion.div>
    </div>
  } 
  else if(index % 4 == 1){
    return <div className="w-full h-full flex-1 min-h-0 min-w-0 flex flex-col">
      {
        rest.length > 0 && <Window index={index+1} items={rest} firstWindow={false} />
      }

      <motion.div 
      initial={{width: 0}}
      animate={{width: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      key={first.id}
      className="w-full h-full flex-1 min-w-0 min-h-0 border border-t-2 border-secondary">
        {toRender(first)}
      </motion.div>
    </div>
  }
  else if(index % 4 == 2){
    return <div className="w-full h-full flex-1 min-w-0 min-h-0 flex flex-row">
      

      <motion.div
      initial={{height: 0}}
      animate={{height: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      key={first.id}
      className="w-full h-full flex-1 min-w-0 min-h-0 border border-r-2 border-secondary">
        {toRender(first)}
      </motion.div>

      {
        rest.length > 0 && <Window index={index+1} items={rest} firstWindow={false}></Window>
      }
    </div>
  }
  else if(index % 4 == 3){
    return <div className="w-full h-full flex flex-col flex-1 min-w-0 min-h-0">
      

      <motion.div
      initial={{width: 0}}
      animate={{width: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      key={first.id}
      className="w-full h-full flex-1 min-h-0 border border-b-2 border-secondary">
        {toRender(first)}
      </motion.div>

      {
        rest.length > 0 && <Window index={index+1} items={rest} firstWindow={false}></Window>
      }
    </div>
  }
}