import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import queue as Q

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        self.cores = 0
        self.bits = 0
        self.scored_on_locations = dict()
        self.damaged_on_locations = dict()
    
    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        if not len(self.scored_on_locations) == 0:
            for k in self.scored_on_locations:
                gamelib.debug_write(f'My edge at {k} for {self.scored_on_locations[k]} dmg')
            self.scored_on_locations = dict()
        if not len(self.damaged_on_locations) == 0:
            for k in self.damaged_on_locations:
                dmg = self.damaged_on_locations[k]
                if dmg > 0:
                    gamelib.debug_write(f'My wall at {k} for {dmg} dmg')
            #self.damaged_on_locations = dict()
        game_state = gamelib.GameState(self.config, turn_state)
        #gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        #game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.
        self.cores = game_state.get_resource(game_state.CORES)
        self.bits = game_state.get_resource(game_state.BITS)
        #self.starter_strategy(game_state)
        self.basic_strategy(game_state)
        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    def get_cheapest_wall(self, game_state):
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        cost = 0
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit
                cost = unit_class.cost
        return cheapest_unit, cost

    def basic_strategy(self, game_state):
        #self.build_first_line_cheapest_wall(game_state)
        #self.build_basic_attackers(game_state)
        if game_state.turn_number >= 1:
            self.replace_defense(game_state)
        self.basic_defense(game_state)
        self.advanced_defense(game_state)
        self.spawn_least_damage(game_state)

    def replace_defense(self, game_state):
        # Replace destructor
        for k in self.damaged_on_locations:
            location = [k // 100, k % 100]
            if game_state.contains_stationary_unit(location):
                unit = game_state.contains_stationary_unit(location)
                if (not unit.unit_type == DESTRUCTOR and unit.stability <= gamelib.GameUnit(unit.unit_type, game_state.config).stability / 3 * 2 ) or unit.stability <= gamelib.GameUnit(unit.unit_type, game_state.config).stability / 2:
                    game_state.attempt_remove(location)
            else:
                self.build_wall(game_state, DESTRUCTOR, location)

    def basic_defense(self, game_state):
        # basic left and right
        destructors_points = [[0, 13], [7, 11]]
        filters_points = [[1, 13], [2, 13], [3, 12], [4, 11], [5, 11], [6, 11]]
        self.defense_level(game_state, destructors_points, filters_points)
        # basic middle
        destructors_points = [[10, 11], [12, 11]]
        filters_points = [[8, 11], [9, 11], [11, 11]]
        self.defense_level(game_state, destructors_points, filters_points)

    def reverse_locations(self, locations):
        rlocations = []
        for location in locations:
            rlocations.append([27 - location[0], location[1]])
        return rlocations
    def encodelocation(self, location):
        return location[0] * 100 + location[1]

    def decodelocation(self, key):
        return [key // 100, key % 100]

    def eculid_distance(self, game_state, key1, key2):
        loc1 = self.decodelocation(key1)
        loc2 = self.decodelocation(key2)
        return game_state.game_map.distance_between_locations(loc1, loc2)

    def advanced_defense(self, game_state):
        destructors = [[3, 13], [1, 12], [2, 12], [2, 11], [3, 11], [5, 9], [6, 9], [7, 9], [8, 9], [9, 9], [10, 9], [11, 9], [12, 9]]
        reversed_destructors = self.reverse_locations(destructors)
        all_locations = destructors + reversed_destructors
        dictionary = dict()
        for location in all_locations:
            dictionary[self.encodelocation(location)] = 999999

        for k in self.scored_on_locations:
            for l in all_locations:
                dictionary[l] = min(self.eculid_distance(game_state, l, k), dictionary[l])
        
        sol = sorted(self.scored_on_locations, key=self.scored_on_locations.get)
        spawn_locations = []
        for location in sol:
            spawn.append(self.decodelocation(location))
        self.build_group_walls(game_state, DESTRUCTOR, spawn_locations)


    def defense_level(self, game_state, destructors_points, filters_points):
        self.build_group_walls(game_state, DESTRUCTOR, destructors_points)
        self.build_group_walls(game_state, FILTER, filters_points)  
        self.build_group_walls(game_state, DESTRUCTOR, destructors_points, True)
        self.build_group_walls(game_state, FILTER, filters_points, True)
               
    def build_group_walls(self, game_state, unit, locations, reverse=False):
        num_success = 0
        wall_locations = []
        for location in locations:
            tmp = location
            if reverse:
                tmp[0] = 27 - tmp[0]
            num_success += self.build_wall(game_state, unit, tmp)    
            if num_success > 0:
                wall_locations.append(tmp)

        if num_success > 0:
            gamelib.debug_write(f'Successfully spawn {DESTRUCTOR} {num_success} times')
            gamelib.debug_write(f'Locations are: {wall_locations}')

    def spawn_least_damage(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        best_location = self.least_damage_spawn_location(game_state, deploy_locations)
        num_spawn = self.bits // game_state.type_cost(PING)
        if num_spawn > 10:
            num_spawn = min(20, num_spawn)
            game_state.attempt_spawn(PING, best_location, int(num_spawn))

    def build_basic_attackers(self, game_state):
        wall_locations = [0, 12, 15, 27]
        q = Q.PriorityQueue()
        for i in wall_locations:
            q.put((self.distance_x(i, 13.5), i))

        priority_locations = []
        while not q.empty():
            priority_locations.append(q.get()[1])
        #gamelib.debug_write(f'heap queue: {priority_locations}')
        locations = []
        for i in priority_locations:
            y = 10 # good bottom level for destructor
            if i >=  25 or i <= 2:
                y = 13 # toppest level for destructor
            location = [i, y]
            locations.append(location)
        self.build_group_walls(game_state, DESTRUCTOR, locations)

    def build_first_line_cheapest_wall(self, game_state):
        basic_wall, cost = self.get_cheapest_wall(game_state)
        locations = []
        for i in range(0, 27):
            if i >= 12 and i <= 15:
                continue
            location = [i, 11]
            locations.append(location)
        self.build_group_walls(game_state, basic_wall, locations)

    def build_wall(self, game_state, unit, location):
        if not game_state.contains_stationary_unit(location) and game_state.game_map.in_arena_bounds(location):
            if game_state.type_cost(unit) <= self.cores:
                success = game_state.attempt_spawn(unit, location)
                self.cores -= success * game_state.type_cost(unit)
                return success
        return 0

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 5, stall with Scramblers and wait to see enemy's base
        if game_state.turn_number < 5:
            self.stall_with_scramblers(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our EMPs to attack them at long range.
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.emp_line_strategy(game_state)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Pings there.

                # Only spawn Ping's every other turn
                # Sending more at once is better since attacks can only hit a single ping at a time
                if game_state.turn_number % 2 == 1:
                    # To simplify we will just check sending them from back left and right
                    ping_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
                    game_state.attempt_spawn(PING, best_location, 1000)

                # Lastly, if we have spare cores, let's build some Encryptors to boost our Pings' health.
                encryptor_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                game_state.attempt_spawn(ENCRYPTOR, encryptor_locations)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place destructors that attack enemy units
        destructor_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)
        
        # Place filters in front of destructors to soak up damage for them
        filter_locations = [[8, 12], [19, 12]]
        game_state.attempt_spawn(FILTER, filter_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(DESTRUCTOR, build_location)

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own firewalls 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining bits to spend lets send out scramblers randomly.
        while game_state.get_resource(game_state.BITS) >= game_state.type_cost(SCRAMBLER) and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        cheapest_unit, cost = self.get_cheapest_wall(game_state)

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        damages = events["damage"]
        self.event_collection(breaches, self.scored_on_locations)
        self.event_collection(damages, self.damaged_on_locations, True)
        '''
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                #gamelib.debug_write("Got scored on at: {}".format(location))
                location = location[0] * 100 + location[1]
                if not location in self.scored_on_locations:
                    self.scored_on_locations[location] = breach[2]
                else:
                    self.scored_on_locations[location] += breach[2]
        '''
        
    def event_collection(self, events, dictionary, is_wall = False):
         for breach in events:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if (not unit_owner_self and not is_wall) or (is_wall and unit_owner_self and breach[2] in [0, 1, 2]):
                #gamelib.debug_write("Got scored on at: {}".format(location))
                location = location[0] * 100 + location[1]
                if not location in dictionary:
                    dictionary[location] = breach[2]
                else:
                    dictionary[location] += breach[2]       
    def distance_x(self, x1, x2):
        return abs(x1 - x2)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
