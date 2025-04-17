"""Update Telepod Exhibit for an open world."""
from ctrando.common import ctenums, memory
from ctrando.locations import locationevent
from ctrando.locations.eventcommand import EventCommand as EC, Operation as OP
from ctrando.locations.locationevent import FunctionID as FID

from ctrando.base import openworldutils as owu

class EventMod(locationevent.LocEventMod):
    """EventMod for Telepod Exhibit"""
    loc_id = ctenums.LocID.TELEPOD_EXHIBIT

    taban_obj = 0xA
    temp_addr = 0x7F0230
    can_eot_addr = 0x7F0232

    @classmethod
    def modify(cls, script: locationevent.LocationEvent):
        """
        Modify Telepod Exhibit for open world.
        - Remove storyline-dependent cutscenes (Marle vanish, 1st return)
        -
        """
        cls.remove_initial_cutscene(script)
        cls.remove_return_cutscene(script)
        cls.make_portal_always_visible(script)
        cls.remove_extras(script)  # Do this last b/c it messes with numbering


    @classmethod
    def remove_initial_cutscene(cls, script: locationevent.LocationEvent):
        """
        Remove the scene that plays when first entering the telepod exhibit.
        """
        start, end = script.get_function_bounds(0, FID.STARTUP)

        pos = script.find_exact_command(
            EC.if_mem_op_value(0x7F0210, OP.EQUALS, 0, 1),
            start, end)

        script.insert_commands(EC.end_cmd().to_bytearray(), pos)
        script.delete_commands_range(pos+1, end+1)

    @classmethod
    def remove_return_cutscene(cls, script: locationevent.LocationEvent):
        """
        Remove the scene the plays when first returning from 600AD.
        """

        start, end = script.get_function_bounds(1, FID.STARTUP)
        pos = script.find_exact_command(
            EC.if_mem_op_value(memory.Memory.STORYLINE_COUNTER,
                               OP.LESS_THAN, 0x27, 1),
            start, end
        )
        script.delete_jump_block(pos)

    @classmethod
    def make_portal_always_visible(cls, script: locationevent.LocationEvent):
        """
        Have the portal always be available.
        """
        start, end = script.get_function_bounds(0x19, FID.STARTUP)
        pos = script.find_exact_command(
            EC.if_mem_op_value(memory.Memory.STORYLINE_COUNTER,
                               OP.LESS_THAN, 0x27, 1),
            start, end
        )
        script.delete_jump_block(pos)

        pos = script.find_exact_command(EC.if_storyline_counter_lt(0x48))

        script.replace_jump_cmd(pos, EC.if_mem_op_value(cls.can_eot_addr, OP.EQUALS, 0))
        script.insert_commands(
            owu.get_can_eot_func(cls.temp_addr, cls.can_eot_addr).get_bytearray(), pos
        )

    @classmethod
    def remove_extras(cls, script: locationevent.LocationEvent):
        """
        Actually remove unneeded objects: NPC Taban, NPC Lucca, crowd,
        pendant, lightning bolts,
        """
        remove_ids = list(range(0x18, 0x9, -1))
        for obj_id in remove_ids:
            script.remove_object(obj_id)
