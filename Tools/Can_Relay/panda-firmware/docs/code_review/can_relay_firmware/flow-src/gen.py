#!/usr/bin/env python3
# A5 flowchart generator: single source of truth -> mermaid + drawio, then verify 1:1
import re, sys, html
from xml.sax.saxutils import escape as xesc

SG = "safety_seer_gate.h"

# node: (id, label, loc, shape)  shape: p=process d=decision t=terminator g=global/state
# edge: (src, dst, label)

D1_NODES = [
 ("RX_BUS","CAN frame on wire (bus0=Seer, bus2=Motor)","hardware","t"),
 ("RX_ISR","CANx_RX0_IRQ_Handler -> can_rx(can_number)","bxcan.h:217,221,225 -> bxcan.h:167","p"),
 ("RX_FMP","while ((CAN->RF0R and CAN_RF0R_FMP0) != 0)","bxcan.h:170","d"),
 ("RX_EXIT","ISR return","bxcan.h:213-214","t"),
 ("RX_BUILD","build CANPacket_t to_push: extended/rtr/addr/dlc/bus/data","bxcan.h:177-187","p"),
 ("RX_FWDHOOK","safety_fwd_hook(bus_number, to_push)","bxcan.h:190 -> safety.h:75","p"),
 ("RX_RELAYMAL","relay_malfunction ?","safety.h:76","d"),
 ("RX_FWD_NEG","return -1 (no forward)","safety.h:76","p"),
 ("GATE_ENTRY","seer_gate_fwd_hook(): addr=GET_ADDR(to_fwd); bus_fwd=-1","%s:279-281"%SG,"p"),
 ("GATE_EDGE","pc_authority edge: rise -> seer_freeze_snapshot(); fall -> seer_frozen_valid=0","%s:285-293"%SG,"p"),
 ("GATE_CACHE","cache update: 0x581-0x584 rtr=0 -> seer_cache_store_resp(); 0x701-0x704 rtr=0 -> guard cache","%s:296-307"%SG,"p"),
 ("GATE_EMU","cover = (seer_cover_until_us - microsecond_timer_get()) > 0; emulate = cover or pc_authority","%s:309,314"%SG,"p"),
 ("GATE_B0","bus_num == 0 ? (Seer -> Motor)","%s:316"%SG,"d"),
 ("B0_SDO","emulate and 0x601 <= addr <= 0x604 and rtr == 0 ?","%s:317"%SG,"d"),
 ("B0_ISREAD","data[0] == 0x40 (SDO upload/read) ?","%s:319"%SG,"d"),
 ("B0_CACHEREPLY","seer_cache_reply(): seer_cache match, or seer_frozen when pc_authority and motion obj; send only if found","%s:320 / :208-248"%SG,"p"),
 ("B0_FWD2_RD","bus_fwd = 2 (read also forwarded to motor)","%s:321"%SG,"p"),
 ("B0_FAKEACK","seer_fake_ack(): synth 0x60 idx sub -> bus0 (write/abort/segment all dropped)","%s:323 / :250-258"%SG,"p"),
 ("B0_FWDNEG_W","bus_fwd = -1","%s:324"%SG,"p"),
 ("B0_GUARD","emulate and 0x701 <= addr <= 0x704 and rtr != 0 ?","%s:326"%SG,"d"),
 ("B0_GUARD_SEND","seer_guard_valid[gn] ? seer_send_bus0(0x700+gn, guard cache)","%s:327-330"%SG,"p"),
 ("B0_GUARD_FWD","bus_fwd = 2 (guard RTR also to motor)","%s:331"%SG,"p"),
 ("B0_BLOCKHOME","seer_block_homing and 0x601-0x604 and rtr==0 and seer_is_homing_write() ?","%s:332-333 / :49-57"%SG,"d"),
 ("B0_HOME_ACK","seer_fake_ack(); bus_fwd = -1 (homing trigger dropped)","%s:341-342"%SG,"p"),
 ("B0_TRANSPARENT","bus_fwd = 2 (transparent)","%s:344"%SG,"p"),
 ("GATE_B2","bus_num == 2 ? (Motor -> Seer)","%s:346"%SG,"d"),
 ("B2_IS_ECHO","0x600 <= addr <= 0x604 ?","%s:347"%SG,"d"),
 ("B2_ECHO_BLOCK","bus_fwd = -1 (block PC command echo)","%s:348"%SG,"p"),
 ("B2_IS_SUP","emulate and (0x581-0x584 or 0x701-0x704) ?","%s:349-350"%SG,"d"),
 ("B2_SUP_BLOCK","bus_fwd = -1 (suppress real motor response)","%s:351"%SG,"p"),
 ("B2_TRANSPARENT","bus_fwd = 0 (motor/guard response -> Seer)","%s:353"%SG,"p"),
 ("GATE_OTHERBUS","bus_fwd = -1 (any other bus)","%s:355-357"%SG,"p"),
 ("GATE_RET","return bus_fwd","%s:358"%SG,"p"),
 ("RX_FWDCHK","bus_fwd_num != -1 ?","bxcan.h:191","d"),
 ("RX_COPY","copy to_push -> to_send (addr/rtr/dlc/data)","bxcan.h:192-201","p"),
 ("CAN_SEND","can_send(to_send, bus_fwd_num, skip_tx_hook = true)","bxcan.h:202 -> can_common.h:236","p"),
 ("SEND_TXHOOK","skip_tx_hook or safety_tx_hook() != 0 ?","can_common.h:237","d"),
 ("SEND_BUSCHK","bus_number < BUS_CNT ?","can_common.h:238","d"),
 ("SEND_GMLAN","bus 3 and can_num_lookup == 0xFF -> bitbang_gmlan(); gmlan_send_errs","can_common.h:240-241","p"),
 ("SEND_PUSH","can_push(can_queues[bus]); can_fwd_errs += fail","can_common.h:243","p"),
 ("SEND_PROC","process_can(CAN_NUM_FROM_BUS_NUM(bus_number))","can_common.h:244","p"),
 ("SEND_REJECT","blocked_msg_cnt++; rejected=1; can_push(can_rx_q); can_send_errs","can_common.h:248-250","p"),
 ("TX_IRQ","CANx_TX_IRQ_Handler -> process_can(n)","bxcan.h:216,220,224","t"),
 ("PROC_ENTRY","process_can(): can_number != 0xff ?","bxcan.h:100-101","d"),
 ("PROC_TME","(CAN->TSR and CAN_TSR_TME0) == TME0 (mailbox 0 empty) ?","bxcan.h:110","d"),
 ("PROC_RQCP","TSR and RQCP0 -> can_txd_cnt++; TXOK0 -> push TX echo into can_rx_q; clear RQCP0","bxcan.h:112-144","p"),
 ("PROC_POP","can_pop(can_queues[bus_number]) ?","bxcan.h:146","d"),
 ("PROC_TX","load sTxMailBox[0] TIR/TDTR/TDLR/TDHR (+RTR bit), set TXRQ","bxcan.h:149-155","p"),
 ("PROC_EP3","usb_cb_ep3_out_complete() -> resume USB OUT ep3 if paused","bxcan.h:157 -> usb_comms.h:98-102","p"),
 ("PROC_RET","process_can() returns","bxcan.h:161-163","t"),
 ("RX_RXHOOK","safety_rx_hook(to_push) (seer gate uses default_rx_hook -> true); can_rx_errs += fail","bxcan.h:205 / safety.h:63 / safety_defaults.h:6-9","p"),
 ("RX_IGN","ignition_can_hook(): bus0 addr 0x160/0x348/0x9E only; ignition_can_cnt=0","bxcan.h:206 -> can_common.h:200-226","p"),
 ("RX_PUSHQ","can_push(can_rx_q) -> host USB; can_send_errs += fail","bxcan.h:209","p"),
 ("RX_RELEASE","CAN->RF0R or= CAN_RF0R_RFOM0 (release FIFO slot)","bxcan.h:212","p"),
 ("SCE_IRQ","CANx_SCE_IRQ_Handler -> can_sce()","bxcan.h:218,222,226 -> bxcan.h:72","t"),
 ("SCE_ERR","can_err_cnt += 1; llcan_clear_send(CAN)","bxcan.h:94-95 / llbxcan.h:123","p"),
]
D1_EDGES = [
 ("RX_BUS","RX_ISR",""),
 ("RX_ISR","RX_FMP",""),
 ("RX_FMP","RX_BUILD","FIFO not empty"),
 ("RX_FMP","RX_EXIT","FIFO empty"),
 ("RX_BUILD","RX_FWDHOOK",""),
 ("RX_FWDHOOK","RX_RELAYMAL",""),
 ("RX_RELAYMAL","RX_FWD_NEG","true"),
 ("RX_RELAYMAL","GATE_ENTRY","false"),
 ("GATE_ENTRY","GATE_EDGE",""),
 ("GATE_EDGE","GATE_CACHE",""),
 ("GATE_CACHE","GATE_EMU",""),
 ("GATE_EMU","GATE_B0",""),
 ("GATE_B0","B0_SDO","yes"),
 ("GATE_B0","GATE_B2","no"),
 ("B0_SDO","B0_ISREAD","yes"),
 ("B0_SDO","B0_GUARD","no"),
 ("B0_ISREAD","B0_CACHEREPLY","read"),
 ("B0_CACHEREPLY","B0_FWD2_RD",""),
 ("B0_ISREAD","B0_FAKEACK","else (write / abort / segment)"),
 ("B0_FAKEACK","B0_FWDNEG_W",""),
 ("B0_GUARD","B0_GUARD_SEND","yes"),
 ("B0_GUARD_SEND","B0_GUARD_FWD",""),
 ("B0_GUARD","B0_BLOCKHOME","no"),
 ("B0_BLOCKHOME","B0_HOME_ACK","yes"),
 ("B0_BLOCKHOME","B0_TRANSPARENT","no"),
 ("GATE_B2","B2_IS_ECHO","yes"),
 ("GATE_B2","GATE_OTHERBUS","no (bus 1)"),
 ("B2_IS_ECHO","B2_ECHO_BLOCK","yes"),
 ("B2_IS_ECHO","B2_IS_SUP","no"),
 ("B2_IS_SUP","B2_SUP_BLOCK","yes"),
 ("B2_IS_SUP","B2_TRANSPARENT","no"),
 ("B0_FWD2_RD","GATE_RET",""),
 ("B0_FWDNEG_W","GATE_RET",""),
 ("B0_GUARD_FWD","GATE_RET",""),
 ("B0_HOME_ACK","GATE_RET",""),
 ("B0_TRANSPARENT","GATE_RET",""),
 ("B2_ECHO_BLOCK","GATE_RET",""),
 ("B2_SUP_BLOCK","GATE_RET",""),
 ("B2_TRANSPARENT","GATE_RET",""),
 ("GATE_OTHERBUS","GATE_RET",""),
 ("GATE_RET","RX_FWDCHK",""),
 ("RX_FWD_NEG","RX_FWDCHK",""),
 ("RX_FWDCHK","RX_COPY","!= -1"),
 ("RX_FWDCHK","RX_RXHOOK","== -1 (dropped)"),
 ("RX_COPY","CAN_SEND",""),
 ("CAN_SEND","SEND_TXHOOK",""),
 ("SEND_TXHOOK","SEND_BUSCHK","allowed"),
 ("SEND_TXHOOK","SEND_REJECT","blocked"),
 ("SEND_BUSCHK","SEND_GMLAN","bus 3 gmlan"),
 ("SEND_BUSCHK","SEND_PUSH","normal bus"),
 ("SEND_PUSH","SEND_PROC",""),
 ("SEND_PROC","PROC_ENTRY",""),
 ("SEND_GMLAN","RX_RXHOOK","return"),
 ("SEND_REJECT","RX_RXHOOK","return"),
 ("TX_IRQ","PROC_ENTRY",""),
 ("PROC_ENTRY","PROC_TME","yes"),
 ("PROC_ENTRY","PROC_RET","can_number == 0xff"),
 ("PROC_TME","PROC_RQCP","empty"),
 ("PROC_TME","PROC_RET","mailbox busy"),
 ("PROC_RQCP","PROC_POP",""),
 ("PROC_POP","PROC_TX","packet popped"),
 ("PROC_POP","PROC_RET","tx queue empty"),
 ("PROC_TX","PROC_EP3",""),
 ("PROC_EP3","PROC_RET",""),
 ("PROC_RET","RX_RXHOOK","return into can_rx"),
 ("RX_RXHOOK","RX_IGN",""),
 ("RX_IGN","RX_PUSHQ",""),
 ("RX_PUSHQ","RX_RELEASE",""),
 ("RX_RELEASE","RX_FMP","next frame"),
 ("SCE_IRQ","SCE_ERR","bus error / error-passive"),
]

D2_NODES = [
 ("U_HOST","Host: USB vendor control transfer (bRequest, wValue, wIndex)","host tool","t"),
 ("U_IRQ","OTG_FS_IRQ_Handler -> usb_irqhandler()","stm32fx/llusb.h:23-30 -> usb.h:655","p"),
 ("U_SETUP","usb_setup(): switch on setup packet","usb.h:479, called usb.h:845","d"),
 ("U_DEFAULT","default branch: resp_len = usb_cb_control_msg(setup ptr, resp)","usb.h:642","p"),
 ("U_SW","usb_cb_control_msg(): switch (setup->b.bRequest)","usb_comms.h:109,113","d"),
 ("U_E8","0xe8: set_intercept_relay(wValue != 0)","usb_comms.h:406-407 / harness.h:21-36","p"),
 ("U_E8_COVER","seer_cover_until_us = microsecond_timer_get() + SEER_COVER_US (300 ms), set for BOTH engage and disengage","usb_comms.h:408 / %s:59-60"%SG,"p"),
 ("U_E9","0xe9: pc_authority = (wValue != 0)","usb_comms.h:410-411","p"),
 ("U_EA","0xea: resp[0] = seer_homing_cmd(wValue != 0, wIndex); resp_len = 1","usb_comms.h:417-419","p"),
 ("U_EA_STOPQ","seer_homing_cmd(): start == false ?","%s:547-549"%SG,"d"),
 ("U_EA_ABORT","non-terminal -> seer_home_cancel_frames() (0x60FB.4 = 0); state = ERR_ABORT; return true","%s:550-552"%SG,"p"),
 ("U_EA_IDLE","terminal -> state = IDLE; return true","%s:552-555"%SG,"p"),
 ("U_EA_INTERLOCK","start: pc_authority and current_safety_mode == 30 and seer_home_is_terminal ?","%s:558-560"%SG,"d"),
 ("U_EA_REJECT","return false (resp[0] = 0)","%s:558-560"%SG,"p"),
 ("U_EA_START","speed = wIndex or 2500; stage_reset(); seen/done/reached masks = 0; state = SEER_HOME_ENABLE","%s:561-567"%SG,"p"),
 ("U_EB","0xeb: resp = state, done_mask, seen_active, elapsed_s lo/hi, DI node3, DI node4, reached_mask (read only)","usb_comms.h:440-449","p"),
 ("U_EB_DI","seer_home_digital_in(n): seer_home_cached_sub(n, 0x6000, 0x01) else 0xFF","%s:519-525"%SG,"p"),
 ("U_EC","0xec: seer_block_homing = (wValue != 0); resp[0] = value","usb_comms.h:425-428","p"),
 ("U_C3","0xc3: resp_len = get_can_health_pkt(resp, wValue)","usb_comms.h:229-230 -> :46","p"),
 ("U_C3_BUS","bus < 3 and bus_config[bus].can_num_lookup < 3 ?","usb_comms.h:51-53","d"),
 ("U_C3_ESR","esr = CANIF_FROM_CAN_NUM(can_num)->ESR (bxCAN F4); STM32H7 leaves esr = 0","usb_comms.h:54-61","p"),
 ("U_C3_FILL","fill can_health_t: error_warning/passive, bus_off, LEC, REC, TEC (read only)","usb_comms.h:65-72","p"),
 ("U_DC","0xdc: set_safety_mode(wValue, wIndex)","usb_comms.h:309-310","p"),
 ("U_DC_MODE","set_safety_mode(): set_safety_hooks(); case SAFETY_SEER_GATE (30) -> heartbeat_counter=0, heartbeat_lost=false, can_silent=ALL_CAN_LIVE, relay NOT touched; can_init_all()","main.c:71-143 (case at :124-131)","p"),
 ("U_F3","0xf3: heartbeat_counter=0; heartbeat_lost=false; heartbeat_disabled=false; heartbeat_engaged=(wValue==1)","usb_comms.h:484-490","p"),
 ("U_RESP","return resp_len -> USB_WritePacket(resp, min(resp_len, wLength))","usb.h:642-646","t"),
 ("S_COVER","STATE seer_cover_until_us -> cover window","%s:60, read :309"%SG,"g"),
 ("S_AUTH","STATE pc_authority","%s:37"%SG,"g"),
 ("S_EMU","STATE emulate = cover or pc_authority -> SDO write drop + fake ack, read served from cache, bus2 real response suppressed","%s:314-354"%SG,"g"),
 ("S_FREEZE","STATE seer_frozen / seer_frozen_valid: set on pc_authority rising edge at next fwd frame, cleared on falling edge","%s:285-293, :102-103"%SG,"g"),
 ("S_BLOCK","STATE seer_block_homing -> drop Seer homing writes in non-emulate window","%s:43, used :332-342"%SG,"g"),
 ("S_HOMESTATE","STATE seer_home_state (+ masks, elapsed) advanced by seer_homing_tick() at 8 Hz","%s:443-450, :571"%SG,"g"),
 ("S_HOMEGATE","seer_homing_tick() interlock: !pc_authority or current_safety_mode != 30 -> cancel frames + ERR_ABORT","%s:576-580"%SG,"d"),
 ("S_HBEAT","STATE heartbeat_counter / heartbeat_lost / heartbeat_disabled / heartbeat_engaged","main.c:210-212, 227-284","g"),
 ("S_MODE","STATE current_safety_mode + current_hooks (= seer_gate_hooks at mode 30)","safety.h:58-60, registry :266-275","g"),
 ("S_RELAY","STATE harness relay GPIO: intercept vs passthrough","harness.h:21-36","g"),
]
D2_EDGES = [
 ("U_HOST","U_IRQ",""),
 ("U_IRQ","U_SETUP",""),
 ("U_SETUP","U_DEFAULT","vendor request (not std / WebUSB / MS)"),
 ("U_DEFAULT","U_SW",""),
 ("U_SW","U_E8","0xe8"),
 ("U_SW","U_E9","0xe9"),
 ("U_SW","U_EA","0xea"),
 ("U_SW","U_EB","0xeb"),
 ("U_SW","U_EC","0xec"),
 ("U_SW","U_C3","0xc3"),
 ("U_SW","U_DC","0xdc"),
 ("U_SW","U_F3","0xf3"),
 ("U_E8","U_E8_COVER",""),
 ("U_E8","S_RELAY","writes"),
 ("U_E8_COVER","S_COVER","writes"),
 ("U_E8_COVER","U_RESP","resp_len = 0"),
 ("S_COVER","S_EMU","cover term"),
 ("U_E9","S_AUTH","writes"),
 ("U_E9","U_RESP","resp_len = 0"),
 ("S_AUTH","S_EMU","pc_authority term"),
 ("S_AUTH","S_FREEZE","edge detect"),
 ("S_AUTH","S_HOMEGATE","read"),
 ("U_EA","U_EA_STOPQ",""),
 ("U_EA_STOPQ","U_EA_ABORT","start = 0, running"),
 ("U_EA_STOPQ","U_EA_IDLE","start = 0, terminal"),
 ("U_EA_STOPQ","U_EA_INTERLOCK","start = 1"),
 ("U_EA_INTERLOCK","U_EA_REJECT","no"),
 ("U_EA_INTERLOCK","U_EA_START","yes"),
 ("U_EA_START","S_HOMESTATE","writes ENABLE"),
 ("U_EA_ABORT","S_HOMESTATE","writes ERR_ABORT"),
 ("U_EA_IDLE","S_HOMESTATE","writes IDLE"),
 ("U_EA_START","U_RESP","resp[0] = 1"),
 ("U_EA_ABORT","U_RESP","resp[0] = 1"),
 ("U_EA_IDLE","U_RESP","resp[0] = 1"),
 ("U_EA_REJECT","U_RESP","resp[0] = 0"),
 ("S_HOMEGATE","S_HOMESTATE","ERR_ABORT"),
 ("U_EB","U_EB_DI",""),
 ("U_EB_DI","U_RESP","resp_len = 8"),
 ("S_HOMESTATE","U_EB","read by 0xeb"),
 ("U_EC","S_BLOCK","writes"),
 ("U_EC","U_RESP","resp_len = 1"),
 ("U_C3","U_C3_BUS",""),
 ("U_C3_BUS","U_C3_ESR","yes"),
 ("U_C3_BUS","U_C3_FILL","no (esr = 0)"),
 ("U_C3_ESR","U_C3_FILL",""),
 ("U_C3_FILL","U_RESP","resp_len = sizeof(can_health_t)"),
 ("U_DC","U_DC_MODE",""),
 ("U_DC_MODE","S_MODE","writes"),
 ("U_DC_MODE","U_RESP","resp_len = 0"),
 ("S_MODE","S_HOMEGATE","read"),
 ("U_F3","S_HBEAT","writes"),
 ("U_F3","U_RESP","resp_len = 0"),
 ("S_HBEAT","S_AUTH","heartbeat lost -> pc_authority = false (main.c:263)"),
 ("S_HBEAT","S_RELAY","heartbeat lost -> set_intercept_relay(false) (main.c:262)"),
]

D3_NODES = [
 ("T_MAIN","main() for(;;): enable_can_transceivers(true); LED fade or __WFI - no CAN or homing work in the main loop","main.c:425-478","t"),
 ("T_IRQ","TICK_TIMER IRQ (8 Hz) -> tick_handler()","registered main.c:405-406; body main.c:169","t"),
 ("T_SR","TICK_TIMER->SR != 0 ?","main.c:170","d"),
 ("T_SIREN","set_siren((loop_counter and 1) and (siren_enabled or siren_countdown > 0))","main.c:172","p"),
 ("T_HOMING","seer_homing_tick() - called every 8 Hz tick, unconditional","main.c:177","p"),
 ("T_HOMEGUARD","seer_homing_tick(): seer_home_is_terminal(state) -> return","%s:571-572, :539-543"%SG,"d"),
 ("T_HOMEAUTH","!pc_authority or current_safety_mode != 30 ?","%s:576"%SG,"d"),
 ("T_HOMEABORT","seer_home_cancel_frames() (0x60FB.4 = 0 to node3,4); state = ERR_ABORT; return","%s:577-579"%SG,"p"),
 ("T_HOMESW","switch (seer_home_state) - one stage per tick (see homing state machine)","%s:582-708"%SG,"p"),
 ("T_DEC","loop_counter == 0 ? (decimate 8 Hz -> 1 Hz)","main.c:180","d"),
 ("T_1HZ","1 Hz block: can_live = pending_can_live; usb_power_mode_tick(); fan_tick(); LED green = controls_allowed; LED blue = power save","main.c:181-207","p"),
 ("T_HBINC","heartbeat_counter += 1 (capped at UINT32_MAX)","main.c:210-212","p"),
 ("T_SIRENCD","siren_countdown > 0 -> siren_countdown -= 1","main.c:214-216","p"),
 ("T_CA","controls_allowed ? controls_allowed_countdown = 30 : countdown -= 1","main.c:218-224","p"),
 ("T_ENG","controls_allowed and !heartbeat_engaged -> mismatches += 1; >= 3 -> controls_allowed = 0","main.c:227-234","p"),
 ("T_HBDIS","heartbeat_disabled ?","main.c:236","d"),
 ("T_HBLOST","heartbeat_counter >= (check_started() ? HEARTBEAT_IGNITION_CNT_ON 5 : _OFF 2) ?","main.c:238 / :164-165","d"),
 ("T_LOSTLOG","log; controls_allowed_countdown > 0 -> siren_countdown = 5, controls_allowed_countdown = 0","main.c:239-246","p"),
 ("T_LOSTFLAG","is_car_safety_mode(current_safety_mode) -> heartbeat_lost = true","main.c:249-251","p"),
 ("T_SILENT","current_safety_mode != SAFETY_SILENT -> set_safety_mode(SAFETY_SILENT, 0)","main.c:253-255","p"),
 ("T_FAILSAFE","FAIL-SAFE: set_intercept_relay(false); pc_authority = false","main.c:262-263","p"),
 ("T_PWRSAVE","power_save_status != ENABLED -> set_power_save_state(ENABLED); set_ir_power(0); fan = usb_enumerated ? 50 : 0","main.c:265-277","p"),
 ("T_CDP","check_started() and (usb_power_mode != USB_POWER_CDP or !usb_enumerated) -> set_usb_power_mode(CDP)","main.c:281-283","p"),
 ("T_REG","check_registers(); ignition_can_cnt > 2 -> ignition_can = false","main.c:287-292","p"),
 ("T_CNT","uptime_cnt += 1; safety_mode_cnt += 1; ignition_can_cnt += 1","main.c:295-297","p"),
 ("T_STICK","safety_tick(current_rx_checks) - seer gate uses default_rx_checks with len 0, so no lag check runs","main.c:300 / safety.h:158-173 / safety_defaults.h:1-4","p"),
 ("T_LOOPC","loop_counter = (loop_counter + 1) % 8","main.c:303-304","p"),
 ("T_CLR","TICK_TIMER->SR = 0; ISR return","main.c:306-307","t"),
]
D3_EDGES = [
 ("T_MAIN","T_IRQ","preempted by 8 Hz tick IRQ"),
 ("T_IRQ","T_SR",""),
 ("T_SR","T_SIREN","SR != 0"),
 ("T_SR","T_CLR","SR == 0 (body skipped)"),
 ("T_SIREN","T_HOMING",""),
 ("T_HOMING","T_HOMEGUARD",""),
 ("T_HOMEGUARD","T_DEC","terminal state -> return"),
 ("T_HOMEGUARD","T_HOMEAUTH","running"),
 ("T_HOMEAUTH","T_HOMEABORT","yes"),
 ("T_HOMEAUTH","T_HOMESW","no"),
 ("T_HOMEABORT","T_DEC","return"),
 ("T_HOMESW","T_DEC","stage advanced"),
 ("T_DEC","T_1HZ","yes"),
 ("T_DEC","T_LOOPC","no"),
 ("T_1HZ","T_HBINC",""),
 ("T_HBINC","T_SIRENCD",""),
 ("T_SIRENCD","T_CA",""),
 ("T_CA","T_ENG",""),
 ("T_ENG","T_HBDIS",""),
 ("T_HBDIS","T_REG","true (0xf8 debug disable)"),
 ("T_HBDIS","T_HBLOST","false"),
 ("T_HBLOST","T_LOSTLOG","yes (heartbeat lost)"),
 ("T_HBLOST","T_CDP","no"),
 ("T_LOSTLOG","T_LOSTFLAG",""),
 ("T_LOSTFLAG","T_SILENT",""),
 ("T_SILENT","T_FAILSAFE",""),
 ("T_FAILSAFE","T_PWRSAVE",""),
 ("T_FAILSAFE","T_HOMEAUTH","next tick: pc_authority = false -> homing ERR_ABORT"),
 ("T_PWRSAVE","T_CDP",""),
 ("T_CDP","T_REG",""),
 ("T_REG","T_CNT",""),
 ("T_CNT","T_STICK",""),
 ("T_STICK","T_LOOPC",""),
 ("T_LOOPC","T_CLR",""),
]

D4_NODES = [
 ("H_IDLE","IDLE (0)","%s:430, 443"%SG,"t"),
 ("H_ENABLE","ENABLE (1): 0x6040 = 0x86 (fault reset + enable) to node3 and node4","%s:431, 583-588"%SG,"p"),
 ("H_SETSPEED","SET_SPEED (2): 0x6099 = seer_home_speed (default 2500 = 0.1 r/min units)","%s:432, 590-595"%SG,"p"),
 ("H_START","START (3): 0x60FB sub4 = 1 (RstStart); stage_reset(); 0x6098 deliberately not written","%s:433, 597-604"%SG,"p"),
 ("H_WAIT","WAIT (4): every 2nd tick (4 Hz) read 0x6041 and 0x6000.01; seen_active on bit15 == 0, done_mask on the 0 -> 1 transition","%s:434, 606-644"%SG,"p"),
 ("H_RESTORE","RESTORE (8): 0x6060 = 1 (PP), 0x6081 = 30000, 0x6083 = 250, 0x6084 = 250","%s:438, 646-655"%SG,"p"),
 ("H_GOZERO","GOZERO (9): 0x607A = 7882020 (node3) / 7859062 (node4); 0x6040 = 0x3F","%s:439, 657-665"%SG,"p"),
 ("H_GOZERO_W","GOZERO_W (11): every 2nd tick read 0x6064 and 0x6000.01; reached when abs(pos - target) < 57344 counts (1.0 deg)","%s:440, 667-703"%SG,"p"),
 ("H_DONE","DONE (5) terminal","%s:435, 690"%SG,"t"),
 ("H_ERR_TIMEOUT","ERR_TIMEOUT (6) terminal - homing search timed out","%s:436, 640"%SG,"t"),
 ("H_ERR_ABORT","ERR_ABORT (7) terminal - host abort or authority lost","%s:437, 551 / 578 / 706"%SG,"t"),
 ("H_ERR_GOZERO","ERR_GOZERO (10) terminal - origin found but 0 deg return not confirmed","%s:441, 699"%SG,"t"),
 ("H_DEFAULT","default: unknown state value","%s:705-707"%SG,"d"),
 ("H_TICKGUARD","seer_homing_tick() entry: seer_home_is_terminal(state) -> return immediately (absorbing until 0xea)","%s:571-572, 539-543"%SG,"d"),
]
_START_GUARD = "0xea start=1 and pc_authority and safety_mode == 30 and is_terminal (%s:558-566)" % SG
_ABORT_LBL = "!pc_authority or safety_mode != 30 -> cancel frames (%s:576-579), or 0xea start=0 (%s:550-551)" % (SG, SG)
D4_EDGES = [
 ("H_IDLE","H_ENABLE",_START_GUARD),
 ("H_DONE","H_ENABLE",_START_GUARD),
 ("H_ERR_TIMEOUT","H_ENABLE",_START_GUARD),
 ("H_ERR_ABORT","H_ENABLE",_START_GUARD),
 ("H_ERR_GOZERO","H_ENABLE",_START_GUARD),
 ("H_ENABLE","H_SETSPEED","unconditional, next 8 Hz tick (%s:587)"%SG),
 ("H_SETSPEED","H_START","unconditional, next tick (%s:594)"%SG),
 ("H_START","H_WAIT","unconditional, next tick + stage_reset (%s:602-603)"%SG),
 ("H_WAIT","H_RESTORE","done_mask == 0b11 (both steer nodes homed) (%s:630-632)"%SG),
 ("H_WAIT","H_ERR_TIMEOUT","elapsed_s >= SEER_HOME_TIMEOUT_S = 120 s -> cancel frames (%s:635-641)"%SG),
 ("H_RESTORE","H_GOZERO","unconditional, next tick (%s:654)"%SG),
 ("H_GOZERO","H_GOZERO_W","unconditional, next tick + stage_reset (%s:663-664)"%SG),
 ("H_GOZERO_W","H_DONE","reached_mask == 0b11 (%s:689-690)"%SG),
 ("H_GOZERO_W","H_ERR_GOZERO","elapsed_s >= SEER_HOME_ZERO_TMO_S = 30 s, no cancel frames sent (%s:693-700)"%SG),
 ("H_ENABLE","H_ERR_ABORT",_ABORT_LBL),
 ("H_SETSPEED","H_ERR_ABORT",_ABORT_LBL),
 ("H_START","H_ERR_ABORT",_ABORT_LBL),
 ("H_WAIT","H_ERR_ABORT",_ABORT_LBL),
 ("H_RESTORE","H_ERR_ABORT",_ABORT_LBL),
 ("H_GOZERO","H_ERR_ABORT",_ABORT_LBL),
 ("H_GOZERO_W","H_ERR_ABORT",_ABORT_LBL),
 ("H_DEFAULT","H_ERR_ABORT","default case of switch (%s:705-707)"%SG),
 ("H_IDLE","H_TICKGUARD","tick does nothing"),
 ("H_DONE","H_TICKGUARD","tick does nothing"),
 ("H_ERR_TIMEOUT","H_TICKGUARD","tick does nothing"),
 ("H_ERR_ABORT","H_TICKGUARD","tick does nothing"),
 ("H_ERR_GOZERO","H_TICKGUARD","tick does nothing"),
]

D5_NODES = [
 ("C_MAIN","ENTRY main()","main.c:341","t"),
 ("C_TICK","ENTRY tick_handler() - TICK_TIMER 8 Hz ISR","main.c:169 / registered :405","t"),
 ("C_CANRX","ENTRY can_rx() - CANx_RX0 ISR","bxcan.h:167 / :217,221,225","t"),
 ("C_CANTX","ENTRY CANx_TX_IRQ_Handler","bxcan.h:216,220,224","t"),
 ("C_SCE","ENTRY can_sce() - CANx_SCE ISR","bxcan.h:72 / :218,222,226","t"),
 ("C_USB","ENTRY usb_cb_control_msg() - OTG_FS ISR","usb_comms.h:109 / llusb.h:23","t"),
 ("C_EXTI","ENTRY EXTI_IRQ_Handler()","main.c:309","t"),
 ("C_RTC","ENTRY RTC_WKUP_IRQ_Handler()","main.c:325","t"),
 ("C_FWDHOOK","safety_fwd_hook()","safety.h:75","p"),
 ("C_GATE","seer_gate_fwd_hook()","%s:279"%SG,"p"),
 ("C_CACHESTORE","seer_cache_store_resp()","%s:115"%SG,"p"),
 ("C_CACHEREPLY","seer_cache_reply()","%s:208"%SG,"p"),
 ("C_FAKEACK","seer_fake_ack()","%s:250"%SG,"p"),
 ("C_FREEZE","seer_freeze_snapshot()","%s:145"%SG,"p"),
 ("C_MOTION","seer_is_motion_obj()","%s:203"%SG,"p"),
 ("C_ISHOMEWR","seer_is_homing_write()","%s:49"%SG,"p"),
 ("C_SENDB0","seer_send_bus0()","%s:105"%SG,"p"),
 ("C_SENDB2","seer_send_bus2()","%s:456"%SG,"p"),
 ("C_CANSEND","can_send()","can_common.h:236","p"),
 ("C_CANPUSH","can_push() / can_pop()","can_common.h:91 / :73","p"),
 ("C_PROCESS","process_can()","bxcan.h:100","p"),
 ("C_HOMETICK","seer_homing_tick()","%s:571"%SG,"p"),
 ("C_HOMECMD","seer_homing_cmd()","%s:547"%SG,"p"),
 ("C_HOMEWRITE","seer_home_sdo_write()","%s:467"%SG,"p"),
 ("C_HOMEREAD","seer_home_sdo_read()","%s:483"%SG,"p"),
 ("C_HOMECACHED","seer_home_cached() / _cached_sub()","%s:508 / :494"%SG,"p"),
 ("C_HOMECANCEL","seer_home_cancel_frames()","%s:527"%SG,"p"),
 ("C_HOMEDI","seer_home_digital_in()","%s:519"%SG,"p"),
 ("C_ISTERM","seer_home_is_terminal()","%s:539"%SG,"p"),
 ("C_STAGERESET","seer_home_stage_reset()","%s:533"%SG,"p"),
 ("C_ZEROTGT","seer_home_zero_target()","%s:452"%SG,"p"),
 ("C_SETMODE","set_safety_mode()","main.c:71","p"),
 ("C_SETHOOKS","set_safety_hooks()","safety.h:277","p"),
 ("C_RELAY","set_intercept_relay()","harness.h:21","p"),
 ("C_USTIMER","microsecond_timer_get()","timers.h:14","p"),
 ("C_SAFETYTICK","safety_tick()","safety.h:158","p"),
 ("C_INITALL","can_init_all() -> can_init()","can_common.h:184 / bxcan.h:228","p"),
 ("C_LLCLEAR","llcan_clear_send()","stm32fx/llbxcan.h:123","p"),
 ("C_LED","current_board->set_led()","board_declarations.h:29","p"),
 ("G_PCAUTH","GLOBAL pc_authority","%s:37"%SG,"g"),
 ("G_COVER","GLOBAL seer_cover_until_us","%s:60"%SG,"g"),
 ("G_CACHE","GLOBAL seer_cache[24]","%s:70"%SG,"g"),
 ("G_GUARD","GLOBAL seer_guard_data/len/valid[5]","%s:71-73"%SG,"g"),
 ("G_FROZEN","GLOBAL seer_frozen[24] + seer_frozen_valid","%s:102-103"%SG,"g"),
 ("G_BLOCK","GLOBAL seer_block_homing","%s:43"%SG,"g"),
 ("G_HOMEST","GLOBAL seer_home_state + speed/elapsed/tick/poll/seen/done/reached","%s:443-450"%SG,"g"),
 ("G_MODE","GLOBAL current_safety_mode","safety.h:58","g"),
 ("G_HOOKS","GLOBAL current_hooks","safety.h:60","g"),
 ("G_HB","GLOBAL heartbeat_counter / _lost / _disabled / _engaged","main.c:210-212, 227-251","g"),
 ("G_QUEUES","GLOBAL can_rx_q + can_tx1/2/3_q + can_txgmlan_q","can_common.h:52-63","g"),
]
D5_EDGES = [
 ("C_CANRX","C_FWDHOOK","calls"),
 ("C_FWDHOOK","G_HOOKS","reads"),
 ("C_FWDHOOK","C_GATE","dispatch at mode 30"),
 ("C_GATE","C_FREEZE","pc_authority rising edge"),
 ("C_GATE","C_CACHESTORE","calls"),
 ("C_GATE","C_CACHEREPLY","calls"),
 ("C_GATE","C_FAKEACK","calls"),
 ("C_GATE","C_ISHOMEWR","calls"),
 ("C_GATE","C_USTIMER","cover check"),
 ("C_GATE","C_SENDB0","guard cache reply"),
 ("C_GATE","G_PCAUTH","reads"),
 ("C_GATE","G_COVER","reads"),
 ("C_GATE","G_BLOCK","reads"),
 ("C_GATE","G_GUARD","reads/writes"),
 ("C_CACHESTORE","G_CACHE","writes"),
 ("C_CACHEREPLY","G_CACHE","reads"),
 ("C_CACHEREPLY","G_FROZEN","reads"),
 ("C_CACHEREPLY","G_PCAUTH","reads"),
 ("C_CACHEREPLY","C_MOTION","calls"),
 ("C_CACHEREPLY","C_SENDB0","calls"),
 ("C_FAKEACK","C_SENDB0","calls"),
 ("C_FREEZE","G_CACHE","reads"),
 ("C_FREEZE","G_FROZEN","writes"),
 ("C_SENDB0","C_CANSEND","calls (skip_tx_hook = true)"),
 ("C_SENDB2","C_CANSEND","calls (skip_tx_hook = true)"),
 ("C_CANSEND","C_CANPUSH","calls"),
 ("C_CANSEND","C_PROCESS","calls"),
 ("C_CANPUSH","G_QUEUES","reads/writes"),
 ("C_PROCESS","G_QUEUES","pops tx queue"),
 ("C_PROCESS","C_CANPUSH","can_pop / tx echo push"),
 ("C_CANRX","C_CANSEND","forward"),
 ("C_CANRX","G_QUEUES","pushes can_rx_q"),
 ("C_CANTX","C_PROCESS","calls"),
 ("C_SCE","C_LLCLEAR","calls"),
 ("C_TICK","C_HOMETICK","calls 8 Hz"),
 ("C_TICK","C_SETMODE","heartbeat lost -> SILENT"),
 ("C_TICK","C_RELAY","fail-safe passthrough"),
 ("C_TICK","G_PCAUTH","writes false on heartbeat loss"),
 ("C_TICK","G_HB","reads/writes"),
 ("C_TICK","C_SAFETYTICK","calls 1 Hz"),
 ("C_TICK","C_LED","calls"),
 ("C_HOMETICK","C_ISTERM","calls"),
 ("C_HOMETICK","G_PCAUTH","reads"),
 ("C_HOMETICK","G_MODE","reads"),
 ("C_HOMETICK","G_HOMEST","reads/writes"),
 ("C_HOMETICK","C_HOMEWRITE","calls"),
 ("C_HOMETICK","C_HOMEREAD","calls"),
 ("C_HOMETICK","C_HOMECACHED","calls"),
 ("C_HOMETICK","C_HOMECANCEL","calls"),
 ("C_HOMETICK","C_STAGERESET","calls"),
 ("C_HOMETICK","C_ZEROTGT","calls"),
 ("C_HOMECANCEL","C_HOMEWRITE","calls"),
 ("C_HOMEWRITE","C_SENDB2","calls"),
 ("C_HOMEREAD","C_SENDB2","calls"),
 ("C_HOMECACHED","G_CACHE","reads"),
 ("C_USB","C_HOMECMD","0xea"),
 ("C_USB","C_HOMEDI","0xeb"),
 ("C_USB","G_HOMEST","0xeb reads"),
 ("C_USB","G_PCAUTH","0xe9 writes"),
 ("C_USB","G_COVER","0xe8 writes"),
 ("C_USB","C_USTIMER","0xe8"),
 ("C_USB","C_RELAY","0xe8"),
 ("C_USB","G_BLOCK","0xec writes"),
 ("C_USB","C_SETMODE","0xdc"),
 ("C_USB","G_HB","0xf3 writes"),
 ("C_HOMECMD","C_ISTERM","calls"),
 ("C_HOMECMD","C_HOMECANCEL","calls"),
 ("C_HOMECMD","C_STAGERESET","calls"),
 ("C_HOMECMD","G_PCAUTH","reads"),
 ("C_HOMECMD","G_MODE","reads"),
 ("C_HOMECMD","G_HOMEST","writes"),
 ("C_HOMEDI","C_HOMECACHED","calls"),
 ("C_SETMODE","C_SETHOOKS","calls"),
 ("C_SETMODE","C_RELAY","calls"),
 ("C_SETMODE","C_INITALL","calls"),
 ("C_SETHOOKS","G_HOOKS","writes"),
 ("C_SETHOOKS","G_MODE","writes"),
 ("C_INITALL","C_PROCESS","calls"),
 ("C_MAIN","C_SETMODE","init SILENT"),
 ("C_MAIN","C_INITALL","calls"),
 ("C_MAIN","C_LED","calls"),
 ("C_EXTI","G_HB","heartbeat_counter = 0 (main.c:317)"),
 ("C_RTC","C_LED","calls"),
]

DIAGRAMS = [
 ("1-can-rx-path","CAN RX path (bus -> RX0 ISR -> seer gate -> TX queue)",D1_NODES,D1_EDGES,"flowchart"),
 ("2-usb-control-path","USB control path (0xe8/0xe9/0xea/0xeb/0xec/0xc3 -> state)",D2_NODES,D2_EDGES,"flowchart"),
 ("3-tick-path","Main loop tick path (8 Hz tick_handler, heartbeat fail-safe, homing tick)",D3_NODES,D3_EDGES,"flowchart"),
 ("4-homing-state-machine","Homing sequencer state machine (seer_homing_tick)",D4_NODES,D4_EDGES,"state"),
 ("5-common-call-graph","Common call graph and shared globals across the 3 paths",D5_NODES,D5_EDGES,"flowchart"),
]

BAD = ['"', '&', '|', '{', '}', '[', ']', '(', ')', ';', '#']
def check_label(s, where):
    for ch in ['"','&','|','#']:
        if ch in s:
            raise SystemExit("BAD CHAR %r in %s: %s" % (ch, where, s))

# ---------- mermaid ----------
def mermaid(name, title, nodes, edges, kind):
    out = []
    if kind == "state":
        out.append("stateDiagram-v2")
        for nid,label,loc,shape in nodes:
            check_label(label, nid)
            out.append('    state "%s" as %s' % (label, nid))
        for s,d,l in edges:
            check_label(l, "%s->%s"%(s,d))
            out.append('    %s --> %s : %s' % (s,d,l) if l else '    %s --> %s' % (s,d))
    else:
        out.append("flowchart TD")
        for nid,label,loc,shape in nodes:
            check_label(label, nid)
            if shape == "d":
                out.append('    %s{"%s"}' % (nid,label))
            elif shape == "t":
                out.append('    %s(["%s"])' % (nid,label))
            elif shape == "g":
                out.append('    %s[/"%s"/]' % (nid,label))
            else:
                out.append('    %s["%s"]' % (nid,label))
        for s,d,l in edges:
            check_label(l, "%s->%s"%(s,d))
            out.append('    %s -->|"%s"| %s' % (s,l,d) if l else '    %s --> %s' % (s,d))
    return "\n".join(out)

# ---------- layout ----------
def layout(nodes, edges):
    ids = [n[0] for n in nodes]
    idx = {n:i for i,n in enumerate(ids)}
    incoming = {n:0 for n in ids}
    adj = {n:[] for n in ids}
    for s,d,_ in edges:
        adj[s].append(d); incoming[d]+=1
    level = {n:0 for n in ids}
    # longest-path layering with cycle guard
    for _ in range(len(ids)):
        changed=False
        for s,d,_ in edges:
            if level[d] < level[s]+1 and level[s]+1 < len(ids):
                level[d]=level[s]+1; changed=True
        if not changed: break
    rows={}
    for n in ids: rows.setdefault(level[n],[]).append(n)
    pos={}
    W,H,GX,GY = 300,80,340,150
    for lv in sorted(rows):
        for i,n in enumerate(rows[lv]):
            pos[n]=(40+i*GX, 40+lv*GY)
    return pos,W,H

# ---------- drawio ----------
def drawio(diagrams):
    parts=['<mxfile host="a5-code-review" modified="2026-07-28T00:00:00.000Z" agent="A5" version="21.0.0">']
    for name,title,nodes,edges,kind in diagrams:
        pos,W,H = layout(nodes,edges)
        parts.append('  <diagram name="%s">' % xesc(name))
        parts.append('    <mxGraphModel dx="1400" dy="900" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1200" math="0" shadow="0">')
        parts.append('      <root>')
        parts.append('        <mxCell id="0"/>')
        parts.append('        <mxCell id="1" parent="0"/>')
        for nid,label,loc,shape in nodes:
            x,y = pos[nid]
            val = xesc("%s | %s" % (label, loc))
            parts.append('        <mxCell id="%s" value="%s" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>' % (nid,val,x,y,W,H))
        for i,(s,d,l) in enumerate(edges):
            eid = "e_%s_%s_%d" % (s,d,i)
            parts.append('        <mxCell id="%s" value="%s" style="endArrow=classic;html=1;" edge="1" parent="1" source="%s" target="%s"><mxGeometry relative="1" as="geometry"/></mxCell>' % (eid, xesc(l), s, d))
        parts.append('      </root>')
        parts.append('    </mxGraphModel>')
        parts.append('  </diagram>')
    parts.append('</mxfile>')
    return "\n".join(parts)

# 경로는 이 스크립트 위치 기준(저장소 어디서 실행해도 동일)
import os as _os
BASE = _os.path.dirname(_os.path.abspath(__file__))
xml = drawio(DIAGRAMS)
open(BASE+"/a5-flow.drawio","w").write(xml)
mm = {}
for name,title,nodes,edges,kind in DIAGRAMS:
    mm[name]=mermaid(name,title,nodes,edges,kind)
    open(BASE+"/mermaid-%s.mmd"%name,"w").write(mm[name])
# mapping tables
for name,title,nodes,edges,kind in DIAGRAMS:
    with open(BASE+"/map-%s.md"%name,"w") as f:
        f.write("| node id | label | file:line |\n|---|---|---|\n")
        for nid,label,loc,shape in nodes:
            f.write("| `%s` | %s | `%s` |\n" % (nid,label,loc))
print("written. diagrams=%d nodes=%d edges=%d" % (len(DIAGRAMS), sum(len(d[2]) for d in DIAGRAMS), sum(len(d[3]) for d in DIAGRAMS)))
