import type { OutgoingDataType, Window as WindowInterface } from "../interface";
import Web from "./Web";
import ChatBox from "./ChatBox";
import { motion } from "framer-motion";

export default function Window({items, firstWindow=true}: {items: WindowInterface[], firstWindow?: boolean}) {
  
  const toRender = (window: WindowInterface) => {
    switch (window.windowType) {
      case "chatbox" : 
        return <ChatBox sendData={window.props.sendData} />
      case "iframe" :
        return <Web url={window.props.url}></Web>
    }
  }

  const [first, ... rest] = items

  if(first.id % 4 == 0) {
    return <div className="w-full h-full flex flex-row">
      {
        rest.length > 0 && <Window items={rest} firstWindow={false}></Window>
      }

      <motion.div
      initial={firstWindow ? false : { height: 0 }}
      animate={{height: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      className="w-full h-full border border-l-2 border-secondary">
        {toRender(first)}
      </motion.div>
    </div>
  } 
  else if(first.id % 4 == 1){
    return <div className="w-full h-full flex flex-col">
      {
        rest.length > 0 && <Window items={rest} firstWindow={false}></Window>
      }

      <motion.div 
      initial={{width: 0}}
      animate={{width: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      className="w-full h-full border border-t-2 border-secondary">
        {toRender(first)}
      </motion.div>
    </div>
  }
  else if(first.id % 4 == 2){
    return <div className="w-full h-full flex flex-row">
      <motion.div
      initial={{height: 0}}
      animate={{height: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      className="w-full h-full border border-r-2 border-secondary">
        {toRender(first)}
      </motion.div>

      {
        rest.length > 0 && <Window items={rest} firstWindow={false}></Window>
      }
    </div>
  }
  else if(first.id % 4 == 3){
    return <div className="w-full h-full flex flex-col">
      <motion.div
      initial={{width: 0}}
      animate={{width: "100%"}}
      transition={{duration: 0.3, ease: "easeOut"}}
      className="w-full h-full border border-b-2 border-secondary">
        {toRender(first)}
      </motion.div>

      {
        rest.length > 0 && <Window items={rest} firstWindow={false}></Window>
      }
    </div>
  }
}