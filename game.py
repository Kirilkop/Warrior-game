print("\x1b[33m", end="")
import random
import json
import os
import platform
import subprocess
from datetime import datetime
import hashlib


class SpecialAbility:
    def __init__(self, ability_type, **params):
        self.ability_type = ability_type
        self.params = params

        # Устанавливаем параметры по умолчанию для каждого типа способности
        if ability_type == "poison":
            self.params.setdefault('chance', 0)
            self.params.setdefault('damage', 0)
            self.params.setdefault('duration', 1)
            self.params.setdefault('max_stacks', 3)
        elif ability_type == "vampirism":
            self.params.setdefault('chance', 0)
            self.params.setdefault('heal_multiplier', 0.5)
        elif ability_type == "freeze":
            self.params.setdefault('chance', 0)
            self.params.setdefault('duration', 1)
        elif ability_type == "weakness":
            self.params.setdefault('chance', 0)
            self.params.setdefault('duration', 1)
            self.params.setdefault('effect_multiplier', 0.8)
        elif ability_type == "enhancement":
            self.params.setdefault('chance', 0)
            self.params.setdefault('duration', 1)
            self.params.setdefault('effect_multiplier', 1.2)

    def to_dict(self):
        return {
            'ability_type': self.ability_type,
            'params': self.params
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['ability_type'], **data['params'])


class Warrior:
    def __init__(self, name, health, attack, defense, dodge_chance, crit_chance,
                 crit_damage, initiative, armor_ignore=0, attacks_per_turn=1, special_abilities=None):
        self.name = name
        self.health = health
        self.max_health = health
        self.attack = attack
        self.defense = defense
        self.dodge_chance = dodge_chance
        self.crit_chance = crit_chance
        self.crit_damage = crit_damage
        self.initiative = initiative
        self.armor_ignore = armor_ignore
        self.attacks_per_turn = attacks_per_turn
        self.special_abilities = special_abilities or []

        # Статистика
        self.damage_dealt = 0
        self.damage_taken = 0
        self.damage_blocked = 0
        self.kills = 0

        # Эффекты
        self.poison_stacks = 0
        self.poison_duration = {}
        self.frozen_until = 0
        self.weakened_until = 0
        self.weakened_multiplier = 1.0
        self.enhanced_until = 0
        self.enhanced_multiplier = 1.0

    def take_damage(self, damage):
        self.health -= damage
        self.damage_taken += damage
        if self.health < 0:
            self.health = 0

    def heal(self, amount):
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health

    def process_effects(self, current_round):
        # Обработка яда
        if self.poison_stacks > 0:
            poison_damage = 0
            expired_poisons = []

            for stack_id, poison_data in self.poison_duration.items():
                if current_round >= poison_data['expires']:
                    expired_poisons.append(stack_id)
                else:
                    # Находим способность яда
                    poison_ability = None
                    for ability in self.special_abilities:
                        if ability.ability_type == "poison":
                            poison_ability = ability
                            break

                    if poison_ability:
                        poison_damage += poison_ability.params['damage']

            # Наносим урон от яда
            if poison_damage > 0:
                self.take_damage(poison_damage)
                print(f"💀 {self.name} получает {poison_damage} урона от яда")

            # Удаляем просроченные стаки яда
            for stack_id in expired_poisons:
                del self.poison_duration[stack_id]
                self.poison_stacks -= 1

            if self.poison_stacks < 0:
                self.poison_stacks = 0

        # Проверяем заморозку
        if self.frozen_until > 0 and current_round >= self.frozen_until:
            self.frozen_until = 0
            print(f"❄️ {self.name} оттаивает!")

        # Проверяем ослабление
        if self.weakened_until > 0 and current_round >= self.weakened_until:
            self.weakened_until = 0
            self.weakened_multiplier = 1.0
            print(f"💪 {self.name} восстанавливает силы!")

        # Проверяем усиление
        if self.enhanced_until > 0 and current_round >= self.enhanced_until:
            self.enhanced_until = 0
            self.enhanced_multiplier = 1.0
            print(f"📉 {self.name} усиление заканчивается!")

    def is_frozen(self, current_round):
        return self.frozen_until > current_round

    def is_alive(self):
        return self.health > 0

    def calculate_damage(self, target):
        # Проверка на уклонение
        if random.random() * 100 <= target.dodge_chance:
            potential_damage = self.attack - target.defense
            if potential_damage < 1:
                potential_damage = 1
            target.damage_blocked += potential_damage
            return 0, "УКЛОНЕНИЕ!", False

        # Расчет игнорирования брони
        ignored_defense = target.defense * (self.armor_ignore / 100)
        effective_defense = target.defense - ignored_defense

        # Базовый урон с учетом защиты
        base_damage = self.attack - effective_defense
        if base_damage < 1:
            base_damage = 1

        # Применяем ослабление/усиление
        final_damage = int(base_damage * self.enhanced_multiplier * target.weakened_multiplier)

        # Проверка на критический урон
        is_crit = random.random() * 100 <= self.crit_chance
        if is_crit:
            final_damage = int(final_damage * self.crit_damage)
            return final_damage, "КРИТИЧЕСКИЙ УРОН!", True
        else:
            return final_damage, "", False

    def try_apply_special_ability(self, target, current_round):
        """Попытка применения специальных способностей"""
        applied_abilities = []

        for ability in self.special_abilities:
            if random.random() * 100 <= ability.params['chance']:
                if ability.ability_type == "poison":
                    # Проверяем максимальное количество стаков
                    poison_ability = None
                    for ab in self.special_abilities:
                        if ab.ability_type == "poison":
                            poison_ability = ab
                            break

                    if poison_ability and target.poison_stacks < poison_ability.params['max_stacks']:
                        target.poison_stacks += 1
                        stack_id = f"{id(self)}_{current_round}_{random.randint(1000, 9999)}"
                        target.poison_duration[stack_id] = {
                            'expires': current_round + poison_ability.params['duration']
                        }
                        print(f"☠️ {self.name} накладывает яд на {target.name}!")
                        applied_abilities.append("poison")

                elif ability.ability_type == "vampirism":
                    # Вампиризм будет обработан при нанесении урона
                    applied_abilities.append("vampirism")

                elif ability.ability_type == "freeze" and not target.is_frozen(current_round):
                    target.frozen_until = current_round + ability.params['duration']
                    print(f"❄️ {self.name} замораживает {target.name} на {ability.params['duration']} ходов!")
                    applied_abilities.append("freeze")

                elif ability.ability_type == "weakness" and target.weakened_until <= current_round:
                    target.weakened_until = current_round + ability.params['duration']
                    target.weakened_multiplier = ability.params['effect_multiplier']
                    print(f"💢 {self.name} ослабляет {target.name} на {ability.params['duration']} ходов!")
                    applied_abilities.append("weakness")

                elif ability.ability_type == "enhancement" and self.enhanced_until <= current_round:
                    self.enhanced_until = current_round + ability.params['duration']
                    self.enhanced_multiplier = ability.params['effect_multiplier']
                    print(f"⚡ {self.name} усиливается на {ability.params['duration']} ходов!")
                    applied_abilities.append("enhancement")

        return applied_abilities


class Profile:
    def __init__(self, username, password, is_developer=False):
        self.username = username
        self.password_hash = self._hash_password(password)
        self.is_developer = is_developer
        self.wins = 0
        self.losses = 0
        self.rating = 1000

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == self._hash_password(password)

    def add_win(self):
        self.wins += 1
        self.rating += 25

    def add_loss(self):
        self.losses += 1
        self.rating = max(800, self.rating - 15)

    def to_dict(self):
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'is_developer': self.is_developer,
            'wins': self.wins,
            'losses': self.losses,
            'rating': self.rating
        }

    @classmethod
    def from_dict(cls, data):
        profile = cls(data['username'], "temp")
        profile.password_hash = data['password_hash']
        profile.is_developer = data['is_developer']
        profile.wins = data['wins']
        profile.losses = data['losses']
        profile.rating = data['rating']
        return profile


class BattleHistory:
    def __init__(self):
        self.history_file = "battle_history.json"
        self.max_history = 5

    def add_battle(self, battle_data):
        history = self.load_history()
        history.insert(0, battle_data)

        if len(history) > self.max_history:
            history = history[:self.max_history]

        self.save_history(history)

    def load_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_history(self, history):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def show_history(self):
        history = self.load_history()
        clear_screen()
        print("📜 ИСТОРИЯ ПОСЛЕДНИХ БИТВ")
        print("=" * 50)

        if not history:
            print("История битв пуста")
            wait_for_enter()
            return

        for i, battle in enumerate(history, 1):
            print(f"\n--- Битва {i} ---")
            print(f"📅 Дата: {battle['date']}")
            print(f"🎮 Режим: {battle['mode']}")

            print(f"🏆 ПОБЕДИТЕЛЬ:")
            winner = battle['winner']
            print(f"  👤 {winner['player']} - {winner['warrior']}")

            print(f"📊 РЕЗУЛЬТАТЫ:")
            for j, participant in enumerate(battle['participants']):
                place = j + 1
                print(f"  {place}. 👤 {participant['player']} - {participant['warrior']}")

            print(f"⚔️ Раундов: {battle['rounds']}")
            print(f"💥 Общий урон: {battle['total_damage']}")
            print(f"🛡️ Заблокировано урона: {battle['total_blocked']}")

        wait_for_enter()


class Leaderboard:
    def __init__(self):
        self.leaderboard_file = "leaderboard.json"

    def update_leaderboard(self, profiles):
        leaderboard = []
        for profile in profiles:
            total_games = profile.wins + profile.losses
            win_rate = (profile.wins / total_games * 100) if total_games > 0 else 0
            leaderboard.append({
                'username': profile.username,
                'wins': profile.wins,
                'losses': profile.losses,
                'win_rate': win_rate,
                'rating': profile.rating
            })

        # Сортируем по рейтингу
        leaderboard.sort(key=lambda x: x['rating'], reverse=True)

        with open(self.leaderboard_file, 'w', encoding='utf-8') as f:
            json.dump(leaderboard, f, ensure_ascii=False, indent=2)

    def show_leaderboard(self):
        try:
            with open(self.leaderboard_file, 'r', encoding='utf-8') as f:
                leaderboard = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Таблица лидеров пуста")
            wait_for_enter()
            return

        clear_screen()
        print("🏆 ТАБЛИЦА ЛИДЕРОВ")
        print("=" * 50)

        print(f"\n{'Место':<6} {'Игрок':<15} {'Победы':<8} {'Поражения':<10} {'Рейтинг':<10} {'Винрейт':<8}")
        print("-" * 65)

        for i, player in enumerate(leaderboard[:10], 1):
            print(f"{i:<6} {player['username']:<15} {player['wins']:<8} {player['losses']:<10} "
                  f"{player['rating']:<10} {player['win_rate']:.1f}%")

        wait_for_enter()


def clear_screen():
    try:
        if platform.system() == "Windows":
            subprocess.run("cls", shell=True, check=True)
        else:
            subprocess.run("clear", shell=True, check=True)
    except:
        print('\n' * 100)


def wait_for_enter():
    input("\n↵ Нажмите Enter чтобы продолжить...")


class ProfileManager:
    def __init__(self):
        self.profiles_file = "profiles.json"
        self.max_profiles = 10
        self.current_profile = None

    def load_profiles(self):
        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                profiles_data = json.load(f)
                return [Profile.from_dict(data) for data in profiles_data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_profiles(self, profiles):
        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump([profile.to_dict() for profile in profiles], f, ensure_ascii=False, indent=2)

    def create_profile(self):
        clear_screen()
        print("👤 СОЗДАНИЕ ПРОФИЛЯ")
        print("=" * 30)

        profiles = self.load_profiles()

        if len(profiles) >= self.max_profiles:
            print("❌ Достигнуто максимальное количество профилей (10)")
            wait_for_enter()
            return None

        username = input("Введите имя пользователя: ").strip()
        if not username:
            print("❌ Имя пользователя не может быть пустым")
            wait_for_enter()
            return None

        # Проверяем уникальность имени
        for profile in profiles:
            if profile.username.lower() == username.lower():
                print("❌ Пользователь с таким именем уже существует")
                wait_for_enter()
                return None

        password = input("Введите пароль: ")
        if not password:
            print("❌ Пароль не может быть пустым")
            wait_for_enter()
            return None

        # Специальный пароль для разработчика
        is_developer = False
        dev_password = input("Для создания профиля разработчика введите специальный пароль (или Enter для пропуска): ")
        if dev_password == "DevWarriorKop":
            is_developer = True
            print("🔧 Создан профиль разработчика!")

        new_profile = Profile(username, password, is_developer)
        profiles.append(new_profile)
        self.save_profiles(profiles)

        print(f"✅ Профиль '{username}' создан!")
        wait_for_enter()
        return new_profile

    def login(self):
        clear_screen()
        print("🔐 ВХОД В ПРОФИЛЬ")
        print("=" * 30)

        profiles = self.load_profiles()

        if not profiles:
            print("❌ Нет созданных профилей")
            wait_for_enter()
            return None

        print("Существующие профили:")
        for i, profile in enumerate(profiles, 1):
            print(f"{i}. {profile.username}" + (" 🔧" if profile.is_developer else ""))

        try:
            choice = int(input("\nВыберите профиль: ")) - 1
            if choice < 0 or choice >= len(profiles):
                print("❌ Неверный выбор")
                wait_for_enter()
                return None
        except ValueError:
            print("❌ Введите число")
            wait_for_enter()
            return None

        selected_profile = profiles[choice]
        password = input("Введите пароль: ")

        if selected_profile.check_password(password):
            print(f"✅ Вход выполнен как {selected_profile.username}")
            self.current_profile = selected_profile
            wait_for_enter()
            return selected_profile
        else:
            print("❌ Неверный пароль")
            wait_for_enter()
            return None

    def logout(self):
        self.current_profile = None
        print("✅ Выход выполнен")
        wait_for_enter()

    def verify_player_password(self, player_name):
        """Проверка пароля для игрока по имени"""
        profiles = self.load_profiles()
        for profile in profiles:
            if profile.username.lower() == player_name.lower():
                password = input(f"🔐 Введите пароль для профиля {profile.username}: ")
                if profile.check_password(password):
                    print(f"✅ Успешный вход для {profile.username}")
                    return profile
                else:
                    print("❌ Неверный пароль")
                    return None
        return None  # Профиль не найден - игра без профиля


class GameManager:
    def __init__(self):
        self.save_dir = "warrior_saves"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        self.total_slots = 10
        self.battle_history = BattleHistory()
        self.leaderboard = Leaderboard()
        self.profile_manager = ProfileManager()

    def save_warrior(self, warrior, slot):
        if slot < 1 or slot > self.total_slots:
            print(f"❌ Неверный слот. Допустимые слоты: 1-{self.total_slots}")
            return False

        filename = f"{self.save_dir}/warrior_slot_{slot}.json"
        data = {
            "name": warrior.name,
            "health": warrior.max_health,
            "attack": warrior.attack,
            "defense": warrior.defense,
            "dodge_chance": warrior.dodge_chance,
            "crit_chance": warrior.crit_chance,
            "crit_damage": warrior.crit_damage,
            "initiative": warrior.initiative,
            "armor_ignore": warrior.armor_ignore,
            "attacks_per_turn": warrior.attacks_per_turn,
            "special_abilities": [ability.to_dict() for ability in warrior.special_abilities]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Персонаж сохранен в слот {slot}")
        return True

    def load_warrior(self, slot, show_stats=True):
        if slot < 1 or slot > self.total_slots:
            print(f"❌ Неверный слот. Допустимые слоты: 1-{self.total_slots}")
            return None

        filename = f"{self.save_dir}/warrior_slot_{slot}.json"
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if show_stats:
                self.show_warrior_stats(data)

            # Загружаем специальные способности
            special_abilities = []
            for ability_data in data.get('special_abilities', []):
                special_abilities.append(SpecialAbility.from_dict(ability_data))

            warrior = Warrior(
                data["name"], data["health"], data["attack"], data["defense"],
                data["dodge_chance"], data["crit_chance"], data["crit_damage"],
                data["initiative"], data["armor_ignore"], data.get("attacks_per_turn", 1),
                special_abilities
            )
            print(f"✅ Персонаж загружен из слота {slot}")
            return warrior
        except FileNotFoundError:
            print(f"❌ Слот {slot} пуст")
            return None
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return None

    def show_warrior_stats(self, warrior_data):
        print(f"\n📊 ХАРАКТЕРИСТИКИ ПЕРСОНАЖА:")
        print(f"👤 Имя: {warrior_data['name']}")
        print(f"❤️ Здоровье: {warrior_data['health']}")
        print(f"⚔️ Атака: {warrior_data['attack']}")
        print(f"🛡️ Защита: {warrior_data['defense']}")
        print(f"🎯 Шанс уклонения: {warrior_data['dodge_chance']}%")
        print(f"🔥 Шанс критического урона: {warrior_data['crit_chance']}%")
        print(f"💥 Критический урон: {warrior_data['crit_damage']}x")
        print(f"⚡ Инициатива: {warrior_data['initiative']}")
        print(f"🔓 Игнорирование брони: {warrior_data['armor_ignore']}%")
        print(f"👊 Ударов за ход: {warrior_data.get('attacks_per_turn', 1)}")

        # Показываем специальные способности
        special_abilities = warrior_data.get('special_abilities', [])
        if special_abilities:
            print(f"🌟 Специальные способности:")
            for ability in special_abilities:
                if ability['ability_type'] == "poison":
                    print(f"  ☠️ Яд: {ability['params']['chance']}% шанс, {ability['params']['damage']} урона, "
                          f"{ability['params']['duration']} ходов, макс {ability['params']['max_stacks']} стаков")
                elif ability['ability_type'] == "vampirism":
                    print(f"  🩸 Вампиризм: {ability['params']['chance']}% шанс, "
                          f"лечение {ability['params']['heal_multiplier'] * 100}% от урона")
                elif ability['ability_type'] == "freeze":
                    print(f"  ❄️ Заморозка: {ability['params']['chance']}% шанс, "
                          f"{ability['params']['duration']} ходов")
                elif ability['ability_type'] == "weakness":
                    print(f"  💢 Слабость: {ability['params']['chance']}% шанс, "
                          f"{ability['params']['duration']} ходов, множитель {ability['params']['effect_multiplier']}")
                elif ability['ability_type'] == "enhancement":
                    print(f"  ⚡ Усиление: {ability['params']['chance']}% шанс, "
                          f"{ability['params']['duration']} ходов, множитель {ability['params']['effect_multiplier']}")

    def edit_warrior(self, slot):
        if not self.profile_manager.current_profile or not self.profile_manager.current_profile.is_developer:
            print("❌ Только разработчики могут редактировать персонажей")
            wait_for_enter()
            return

        clear_screen()
        print(f"\n=== РЕДАКТИРОВАНИЕ ПЕРСОНАЖА В СЛОТЕ {slot} ===")

        warrior = self.load_warrior(slot, show_stats=False)
        if not warrior:
            return

        filename = f"{self.save_dir}/warrior_slot_{slot}.json"
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\nТекущие характеристики:")
        self.show_warrior_stats(data)

        print(f"\nВведите новые значения (оставьте пустым для сохранения текущего):")

        name = input(f"Имя [{data['name']}]: ").strip()
        health = input(f"Здоровье [{data['health']}]: ").strip()
        attack = input(f"Атака [{data['attack']}]: ").strip()
        defense = input(f"Защита [{data['defense']}]: ").strip()
        dodge_chance = input(f"Шанс уклонения (%) [{data['dodge_chance']}]: ").strip()
        crit_chance = input(f"Шанс критического урона (%) [{data['crit_chance']}]: ").strip()
        crit_damage = input(f"Критический урон [{data['crit_damage']}]: ").strip()
        initiative = input(f"Инициатива [{data['initiative']}]: ").strip()
        armor_ignore = input(f"Игнорирование брони (%) [{data['armor_ignore']}]: ").strip()
        attacks_per_turn = input(f"Ударов за ход [{data.get('attacks_per_turn', 1)}]: ").strip()

        # Обновляем данные
        if name: data['name'] = name
        if health: data['health'] = int(health)
        if attack: data['attack'] = int(attack)
        if defense: data['defense'] = int(defense)
        if dodge_chance: data['dodge_chance'] = float(dodge_chance)
        if crit_chance: data['crit_chance'] = float(crit_chance)
        if crit_damage: data['crit_damage'] = float(crit_damage)
        if initiative: data['initiative'] = int(initiative)
        if armor_ignore: data['armor_ignore'] = float(armor_ignore)
        if attacks_per_turn: data['attacks_per_turn'] = int(attacks_per_turn)

        # Сохраняем обновленного персонажа
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Персонаж в слоте {slot} обновлен!")
        self.show_warrior_stats(data)
        wait_for_enter()

    def delete_warrior(self, slot):
        if not self.profile_manager.current_profile or not self.profile_manager.current_profile.is_developer:
            print("❌ Только разработчики могут удалять персонажей")
            wait_for_enter()
            return

        filename = f"{self.save_dir}/warrior_slot_{slot}.json"
        if os.path.exists(filename):
            os.remove(filename)
            print(f"✅ Персонаж удален из слота {slot}")
        else:
            print(f"❌ Слот {slot} и так пуст")
        wait_for_enter()

    def show_save_slots(self):
        print(f"\n📁 Слоты сохранения (всего {self.total_slots}):")
        empty_slots = []
        for i in range(1, self.total_slots + 1):
            filename = f"{self.save_dir}/warrior_slot_{i}.json"
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                dev_only = " 🔧" if self.profile_manager.current_profile and self.profile_manager.current_profile.is_developer else ""
                print(f"Слот {i}: {data['name']} (HP: {data['health']}, ATK: {data['attack']}){dev_only}")
            else:
                empty_slots.append(str(i))
                print(f"Слот {i}: [ПУСТО]")

        if empty_slots:
            print(f"\n🎯 Свободные слоты: {', '.join(empty_slots)}")

    def create_default_warriors(self):
        default_warriors = [
            {
                "name": "Железный страж", "health": 180, "attack": 12, "defense": 15,
                "dodge_chance": 5.0, "crit_chance": 8.0, "crit_damage": 1.5,
                "initiative": 6, "armor_ignore": 5.0, "attacks_per_turn": 1,
                "special_abilities": []
            },
            {
                "name": "Теневой клинок", "health": 65, "attack": 35, "defense": 2,
                "dodge_chance": 35.0, "crit_chance": 40.0, "crit_damage": 2.8,
                "initiative": 22, "armor_ignore": 60.0, "attacks_per_turn": 2,
                "special_abilities": [
                    SpecialAbility("poison", chance=25, damage=5, duration=3, max_stacks=3).to_dict(),
                    SpecialAbility("vampirism", chance=20, heal_multiplier=0.3).to_dict()
                ]
            }
        ]

        slots_empty = True
        for i in range(1, 3):
            if os.path.exists(f"{self.save_dir}/warrior_slot_{i}.json"):
                slots_empty = False
                break

        if slots_empty:
            print("🎁 Создание стандартных персонажей...")
            for i, warrior_data in enumerate(default_warriors, 1):
                # Создаем воина из данных
                special_abilities = []
                for ability_data in warrior_data.get('special_abilities', []):
                    special_abilities.append(SpecialAbility.from_dict(ability_data))

                warrior = Warrior(
                    warrior_data["name"], warrior_data["health"], warrior_data["attack"],
                    warrior_data["defense"], warrior_data["dodge_chance"], warrior_data["crit_chance"],
                    warrior_data["crit_damage"], warrior_data["initiative"], warrior_data["armor_ignore"],
                    warrior_data.get("attacks_per_turn", 1), special_abilities
                )
                self.save_warrior(warrior, i)
            print(f"✅ 2 стандартных персонажа созданы в слотах 1-2!")
            print("🎯 Свободные слоты для ваших персонажей: 3-10")
            return True
        return False


def create_warrior_interactive():
    clear_screen()
    print(f"\n=== СОЗДАНИЕ ПЕРСОНАЖА ===")
    name = input("Введите имя: ")
    health = int(input("Здоровье: "))
    attack = int(input("Атака: "))
    defense = int(input("Защита: "))
    dodge_chance = float(input("Шанс уклонения (%): "))
    crit_chance = float(input("Шанс критического урона (%): "))
    crit_damage = float(input("Множитель критического урона (например 1.5): "))
    initiative = int(input("Инициатива: "))
    armor_ignore = float(input("Игнорирование брони (%): "))
    attacks_per_turn = int(input("Количество ударов за ход: "))

    # Выбор специальных способностей (до 2)
    print(f"\n🌟 ВЫБОР СПЕЦИАЛЬНЫХ СПОСОБНОСТЕЙ (максимум 2)")
    print("1. ☠️ Яд")
    print("2. 🩸 Вампиризм")
    print("3. ❄️ Заморозка")
    print("4. 💢 Слабость")
    print("5. ⚡ Усиление")
    print("0. Завершить выбор")

    special_abilities = []
    abilities_count = 0

    while abilities_count < 2:
        choice = input(f"\nВыберите способность {abilities_count + 1}/2 (0 для завершения): ")

        if choice == "0":
            break
        elif choice == "1" and abilities_count < 2:
            print("\n☠️ НАСТРОЙКА ЯДА:")
            chance = float(input("Шанс срабатывания (%): "))
            damage = int(input("Урон за ход: "))
            duration = int(input("Длительность (ходы): "))
            max_stacks = int(input("Максимум стаков: "))
            special_abilities.append(SpecialAbility("poison", chance=chance, damage=damage,
                                                    duration=duration, max_stacks=max_stacks))
            abilities_count += 1
            print("✅ Яд добавлен!")

        elif choice == "2" and abilities_count < 2:
            print("\n🩸 НАСТРОЙКА ВАМПИРИЗМА:")
            chance = float(input("Шанс срабатывания (%): "))
            heal_multiplier = float(input("Множитель лечения (например 0.5 для 50% от урона): "))
            special_abilities.append(SpecialAbility("vampirism", chance=chance,
                                                    heal_multiplier=heal_multiplier))
            abilities_count += 1
            print("✅ Вампиризм добавлен!")

        elif choice == "3" and abilities_count < 2:
            print("\n❄️ НАСТРОЙКА ЗАМОРОЗКИ:")
            chance = float(input("Шанс срабатывания (%): "))
            duration = int(input("Длительность (ходы): "))
            special_abilities.append(SpecialAbility("freeze", chance=chance, duration=duration))
            abilities_count += 1
            print("✅ Заморозка добавлена!")

        elif choice == "4" and abilities_count < 2:
            print("\n💢 НАСТРОЙКА СЛАБОСТИ:")
            chance = float(input("Шанс срабатывания (%): "))
            duration = int(input("Длительность (ходы): "))
            effect_multiplier = float(input("Множитель эффекта (например 0.8 для -20% урона): "))
            special_abilities.append(SpecialAbility("weakness", chance=chance, duration=duration,
                                                    effect_multiplier=effect_multiplier))
            abilities_count += 1
            print("✅ Слабость добавлена!")

        elif choice == "5" and abilities_count < 2:
            print("\n⚡ НАСТРОЙКА УСИЛЕНИЯ:")
            chance = float(input("Шанс срабатывания (%): "))
            duration = int(input("Длительность (ходы): "))
            effect_multiplier = float(input("Множитель эффекта (например 1.2 для +20% урона): "))
            special_abilities.append(SpecialAbility("enhancement", chance=chance, duration=duration,
                                                    effect_multiplier=effect_multiplier))
            abilities_count += 1
            print("✅ Усиление добавлено!")

        else:
            print("❌ Неверный выбор или достигнут лимит способностей")

    return Warrior(name, health, attack, defense, dodge_chance, crit_chance,
                   crit_damage, initiative, armor_ignore, attacks_per_turn, special_abilities)


def generate_bot_warrior(bot_number):
    """Генерация случайного персонажа для бота"""
    bot_names = ["Стальной Гром", "Теневой Убийца", "Ледяной Вихрь", "Огненный Демон",
                 "Каменный Страж", "Небесный Воин", "Ядовитый Клинок", "Кровавый Рыцарь",
                 "Молот Судьбы", "Тихий Призрак", "Безумный Берсерк", "Древний Маг"]

    name = f"Бот {bot_number}: {random.choice(bot_names)}"

    # Сбалансированные характеристики для ботов
    health = random.randint(80, 150)
    attack = random.randint(15, 30)
    defense = random.randint(5, 20)
    dodge_chance = random.uniform(5.0, 25.0)
    crit_chance = random.uniform(5.0, 20.0)
    crit_damage = random.uniform(1.5, 2.5)
    initiative = random.randint(5, 20)
    armor_ignore = random.uniform(0.0, 30.0)
    attacks_per_turn = random.randint(1, 2)

    # Случайные способности (0-2 штуки)
    special_abilities = []
    ability_types = ["poison", "vampirism", "freeze", "weakness", "enhancement"]

    num_abilities = random.randint(0, 2)
    if num_abilities > 0:
        chosen_abilities = random.sample(ability_types, num_abilities)

        for ability_type in chosen_abilities:
            if ability_type == "poison":
                special_abilities.append(SpecialAbility("poison",
                                                        chance=random.randint(15, 30),
                                                        damage=random.randint(3, 8),
                                                        duration=random.randint(2, 4),
                                                        max_stacks=random.randint(2, 4)
                                                        ))
            elif ability_type == "vampirism":
                special_abilities.append(SpecialAbility("vampirism",
                                                        chance=random.randint(15, 25),
                                                        heal_multiplier=random.uniform(0.3, 0.6)
                                                        ))
            elif ability_type == "freeze":
                special_abilities.append(SpecialAbility("freeze",
                                                        chance=random.randint(10, 20),
                                                        duration=random.randint(1, 2)
                                                        ))
            elif ability_type == "weakness":
                special_abilities.append(SpecialAbility("weakness",
                                                        chance=random.randint(15, 25),
                                                        duration=random.randint(2, 3),
                                                        effect_multiplier=random.uniform(0.7, 0.9)
                                                        ))
            elif ability_type == "enhancement":
                special_abilities.append(SpecialAbility("enhancement",
                                                        chance=random.randint(15, 25),
                                                        duration=random.randint(2, 3),
                                                        effect_multiplier=random.uniform(1.1, 1.3)
                                                        ))

    return Warrior(name, health, attack, defense, dodge_chance, crit_chance,
                   crit_damage, initiative, armor_ignore, attacks_per_turn, special_abilities)


def show_tutorial():
    """Полное обучение игре"""
    clear_screen()
    print("🎓 ПОЛНОЕ ОБУЧЕНИЕ ИГРЕ 'БИТВА'")
    print("=" * 50)

    print("\n📖 ОСНОВЫ ИГРЫ:")
    print("• Это пошаговая RPG-битва с различными режимами")
    print("• Создавайте персонажей с уникальными характеристиками")
    print("• Сражайтесь в разных режимах: 1x1, 2x2, 3 игрока, 4 игрока")
    print("• Сохраняйте лучших персонажей для будущих битв")

    wait_for_enter()
    clear_screen()

    print("👤 СИСТЕМА ПРОФИЛЕЙ:")
    print("• Создавайте профили с ником и паролем")
    print("• Максимум 10 профилей")
    print("• Профили разработчиков могут создавать и редактировать персонажей")
    print("• Специальный пароль для разработчика: 'DevWarriorKop'")
    print("• Таблица лидеров отслеживает рейтинг игроков")

    wait_for_enter()
    clear_screen()

    print("🎯 ОСНОВНЫЕ ХАРАКТЕРИСТИКИ:")
    print("• Здоровье (HP) - количество урона, которое можно получить")
    print("• Атака - базовый урон атаки")
    print("• Защита - снижает получаемый урон")
    print("• Шанс уклонения (%) - вероятность полностью избежать атаки")
    print("• Шанс критического урона (%) - вероятность нанести критический удар")
    print("• Критический урон - множитель урона при критической атаке")
    print("• Инициатива - определяет порядок хода (чем выше, тем раньше ход)")
    print("• Игнорирование брони (%) - часть урона, игнорирующая защиту")
    print("• Количество ударов - сколько раз персонаж атакует за ход")

    wait_for_enter()
    clear_screen()

    print("🌟 СПЕЦИАЛЬНЫЕ СПОСОБНОСТИ:")
    print("• Можно выбрать до 2 способностей для персонажа")
    print("• ☠️ Яд - наносит урон каждый ход, имеет длительность и максимум стаков")
    print("• 🩸 Вампиризм - восстанавливает здоровье от нанесенного урона")
    print("• ❄️ Заморозка - противник пропускает ходы на определенное время")
    print("• 💢 Слабость - ослабляет противника, уменьшая его урон")
    print("• ⚡ Усиление - усиливает персонажа, увеличивая его урон")

    wait_for_enter()
    clear_screen()

    print("⚔️ МЕХАНИКИ БОЯ:")
    print("• Порядок хода определяется инициативой")
    print("• Каждый персонаж атакует несколько раз за ход (по количеству ударов)")
    print("• Каждая атака проверяется на уклонение, крит и способности отдельно")
    print("• Защита снижает урон: Урон = Атака - Защита")
    print("• Минимальный урон всегда равен 1")
    print("• Уклонение полностью блокирует атаку")
    print("• Критический урон увеличивает урон на множитель")

    wait_for_enter()
    clear_screen()

    print("📊 СТАТИСТИКА И ИСТОРИЯ:")
    print("• Нанесенный урон - общий урон, нанесенный атаками")
    print("• Полученный урон - общий урон, полученный от атак")
    print("• Заблокированный урон - урон, избегнутый через уклонение")
    print("• Убийства - количество поверженных противников")
    print("• История битв сохраняет последние 5 битв")
    print("• Таблица лидеров показывает лучших игроков по рейтингу")

    wait_for_enter()
    clear_screen()

    print("🎮 РЕЖИМЫ ИГРЫ:")
    print("• 1 на 1 - классическая дуэль двух воинов")
    print("• 2 на 2 - командная битва (2 команды по 2 игрока)")
    print("• 3 игрока - королевская битва, каждый сам за себя")
    print("• 4 игрока - масштабная битва, каждый сам за себя")
    print("• Битва с ботами - сражение против компьютерных противников")
    print("• Во всех режимах кроме 1x1 игроки выбирают цели для атаки")

    wait_for_enter()
    clear_screen()

    print("💾 СИСТЕМА СОХРАНЕНИЙ:")
    print("• 10 слотов для сохранения персонажей")
    print("• Стандартные персонажи создаются автоматически")
    print("• Только разработчики могут создавать и редактировать персонажей")
    print("• Сохраняйте персонажей после битв")
    print("• Загружайте сохраненных персонажей для новых битв")

    wait_for_enter()
    clear_screen()

    print("🏆 СТРАТЕГИЧЕСКИЕ СОВЕТЫ:")
    print("• Балансируйте характеристики - не вкладывайтесь только в одно")
    print("• Высокая инициатива позволяет атаковать первым")
    print("• Комбинируйте специальные способности для синергии")
    print("• Высокое уклонение эффективно против сильных атак")
    print("• Игнорирование брони полезно против танков")
    print("• В многопользовательских режимах выбирайте цели стратегически")

    wait_for_enter()


def perform_attack(attacker, defender, round_num, is_multiplayer=False):
    """Универсальная функция атаки для всех режимов"""
    if not defender.is_alive():
        return True  # Цель уже мертва

    print(f"\n  {attacker.name} атакует {defender.name}!")

    for attack_num in range(attacker.attacks_per_turn):
        if not defender.is_alive():
            return True

        damage, message, is_crit = attacker.calculate_damage(defender)

        if damage == 0 and message == "УКЛОНЕНИЕ!":
            print(f"  ⚡ {defender.name} увернулся от атаки!")
        else:
            defender.take_damage(damage)
            attacker.damage_dealt += damage
            if message:
                print(f"  🔥 {message}")
            print(f"  💥 Наносит {damage} урона!")

            # Вампиризм
            for ability in attacker.special_abilities:
                if ability.ability_type == "vampirism" and is_crit:
                    if random.random() * 100 <= ability.params['chance']:
                        heal_amount = int(damage * ability.params['heal_multiplier'])
                        attacker.heal(heal_amount)
                        print(f"  🩸 {attacker.name} восстанавливает {heal_amount} HP!")

            # Специальные способности
            applied_abilities = attacker.try_apply_special_ability(defender, round_num)

            print(f"  ❤️ У {defender.name} осталось {defender.health}/{defender.max_health} здоровья")

            if not defender.is_alive():
                attacker.kills += 1
                print(f"  💀 {defender.name} убит!")
                return True

    return False


def update_profiles_statistics(game_manager, winners, all_players, authenticated_profiles):
    """Обновление статистики только для аутентифицированных профилей"""
    profiles = game_manager.profile_manager.load_profiles()

    # Создаем словарь для быстрого доступа к профилям
    profile_dict = {profile.username: profile for profile in profiles}

    for profile in authenticated_profiles:
        if profile and profile.username in profile_dict:
            if profile.username in winners:
                profile_dict[profile.username].add_win()
            elif profile.username in all_players:
                profile_dict[profile.username].add_loss()

    game_manager.profile_manager.save_profiles(profiles)
    game_manager.leaderboard.update_leaderboard(profiles)


def print_battle_statistics(warriors, player_names, rounds):
    """Печать статистики битвы"""
    print("\n" + "=" * 50)
    print("📊 ПОДРОБНАЯ СТАТИСТИКА БИТВЫ:")

    for i, warrior in enumerate(warriors):
        print(f"\n{warrior.name} ({player_names[i]}):")
        print(f"  Здоровье: {warrior.health}/{warrior.max_health}")
        print(f"  Нанесено урона: {warrior.damage_dealt}")
        print(f"  Получено урона: {warrior.damage_taken}")
        print(f"  Заблокировано урона: {warrior.damage_blocked}")
        print(f"  Убийства: {warrior.kills}")

    print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
    total_damage = sum(w.damage_dealt for w in warriors)
    total_blocked = sum(w.damage_blocked for w in warriors)
    total_kills = sum(w.kills for w in warriors)

    print(f"Количество раундов: {rounds}")
    print(f"Общий нанесенный урон: {total_damage}")
    print(f"Общий заблокированный урон: {total_blocked}")
    print(f"Всего убийств: {total_kills}")


def offer_save_warriors(game_manager, warriors):
    """Предложение сохранить воинов после битвы"""
    if game_manager.profile_manager.current_profile and game_manager.profile_manager.current_profile.is_developer:
        save_choice = input("\n💾 Сохранить персонажей? (y/n): ").lower()
        if save_choice == 'y':
            clear_screen()
            game_manager.show_save_slots()
            for i, warrior in enumerate(warriors):
                slot = int(input(f"Введите слот для сохранения {warrior.name} (1-{game_manager.total_slots}): "))
                game_manager.save_warrior(warrior, slot)


def battle_round_1v1(attacker, defender, round_num):
    print(f"\n--- Раунд {round_num} ---")

    # Обработка эффектов у атакующего
    attacker.process_effects(round_num)
    if not attacker.is_alive():
        print(f"💀 {attacker.name} умер от эффектов перед атакой!")
        return True

    # Проверяем заморозку
    if attacker.is_frozen(round_num):
        print(f"❄️ {attacker.name} заморожен и пропускает ход!")
        return False

    print(f"{attacker.name} атакует {defender.name}!")

    # Множественные атаки
    for attack_num in range(attacker.attacks_per_turn):
        if not defender.is_alive():
            break

        killed = perform_attack(attacker, defender, round_num)
        if killed:
            break

    # Обработка эффектов у защищающегося
    if defender.is_alive():
        defender.process_effects(round_num)

    return False


def run_1v1_battle(warrior1, warrior2, game_manager, player_names, authenticated_profiles):
    clear_screen()
    # Определение кто атакует первым
    if warrior1.initiative > warrior2.initiative:
        attacker, defender = warrior1, warrior2
        attacker_player, defender_player = player_names[0], player_names[1]
        print(f"\n🎯 {warrior1.name} ({attacker_player}) атакует первым (инициатива: {warrior1.initiative})")
    elif warrior2.initiative > warrior1.initiative:
        attacker, defender = warrior2, warrior1
        attacker_player, defender_player = player_names[1], player_names[0]
        print(f"\n🎯 {warrior2.name} ({attacker_player}) атакует первым (инициатива: {warrior2.initiative})")
    else:
        attacker, defender = random.choice([(warrior1, warrior2), (warrior2, warrior1)])
        if attacker == warrior1:
            attacker_player, defender_player = player_names[0], player_names[1]
        else:
            attacker_player, defender_player = player_names[1], player_names[0]
        print(f"\n🎯 Первым атакует {attacker.name} ({attacker_player}) (ничья в инициативе)")

    wait_for_enter()

    # Основной цикл битвы
    round_num = 1
    winner_name = "Ничья"
    winner_warrior = "Ничья"

    while warrior1.is_alive() and warrior2.is_alive():
        clear_screen()
        poison_death = battle_round_1v1(attacker, defender, round_num)

        if poison_death:
            break

        # Проверка на смерть
        if not defender.is_alive():
            print(f"\n💀 {defender.name} пал в бою!")
            print(f"🏆 ПОБЕДИТЕЛЬ: {attacker.name} ({attacker_player})!")
            winner_name = attacker_player
            winner_warrior = attacker.name
            break

        # Смена ролей атакующий/защищающийся
        attacker, defender = defender, attacker
        attacker_player, defender_player = defender_player, attacker_player
        round_num += 1

        # Ограничение на максимальное количество раундов
        if round_num > 50:
            print("\n⏰ Битва затянулась! Ничья!")
            break

        wait_for_enter()

    # Статистика боя
    print_battle_statistics([warrior1, warrior2], player_names, round_num - 1)

    # Сохраняем в историю
    battle_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "1 на 1",
        "winner": {"player": winner_name, "warrior": winner_warrior},
        "participants": [
            {"player": player_names[0], "warrior": warrior1.name},
            {"player": player_names[1], "warrior": warrior2.name}
        ],
        "rounds": round_num - 1,
        "total_damage": warrior1.damage_dealt + warrior2.damage_dealt,
        "total_blocked": warrior1.damage_blocked + warrior2.damage_blocked
    }
    game_manager.battle_history.add_battle(battle_data)

    # Обновляем статистику профилей
    if winner_name != "Ничья":
        update_profiles_statistics(game_manager, [winner_name], player_names, authenticated_profiles)

    # Предложение сохранить персонажей
    offer_save_warriors(game_manager, [warrior1, warrior2])

    wait_for_enter()


def run_2v2_battle(team1, team2, game_manager, player_names, authenticated_profiles):
    """Битва 2 на 2 - командный режим"""
    clear_screen()
    print("⚔️ БИТВА 2 НА 2 - КОМАНДНЫЙ РЕЖИМ")

    # Объединяем всех воинов и сортируем по инициативе
    all_warriors = team1 + team2
    all_warriors.sort(key=lambda w: w.initiative, reverse=True)

    print("\n🎯 Порядок ходов:")
    for i, warrior in enumerate(all_warriors, 1):
        team = "Команда 1" if warrior in team1 else "Команда 2"
        print(f"  {i}. {warrior.name} ({team}) - инициатива: {warrior.initiative}")

    wait_for_enter()

    round_num = 1
    while True:
        clear_screen()
        print(f"--- Раунд {round_num} ---")

        # Показываем состояние команд
        print(f"\n📊 КОМАНДА 1:")
        for warrior in team1:
            status = "❤️" if warrior.is_alive() else "💀"
            print(f"  {status} {warrior.name}: {warrior.health}/{warrior.max_health} HP")

        print(f"\n📊 КОМАНДА 2:")
        for warrior in team2:
            status = "❤️" if warrior.is_alive() else "💀"
            print(f"  {status} {warrior.name}: {warrior.health}/{warrior.max_health} HP")

        # Проверяем победу
        team1_alive = any(warrior.is_alive() for warrior in team1)
        team2_alive = any(warrior.is_alive() for warrior in team2)

        if not team1_alive:
            winner_team = team2
            winner_players = [player_names[2], player_names[3]]
            break
        if not team2_alive:
            winner_team = team1
            winner_players = [player_names[0], player_names[1]]
            break

        # Ходы воинов
        for warrior in all_warriors:
            if not warrior.is_alive():
                continue

            # Обработка эффектов
            warrior.process_effects(round_num)
            if not warrior.is_alive():
                continue

            if warrior.is_frozen(round_num):
                print(f"❄️ {warrior.name} заморожен и пропускает ход!")
                continue

            # Определяем вражескую команду
            if warrior in team1:
                enemy_team = team2
            else:
                enemy_team = team1

            # Выбираем живую цель
            alive_enemies = [enemy for enemy in enemy_team if enemy.is_alive()]
            if not alive_enemies:
                continue

            # Если несколько целей - выбираем случайную
            target = random.choice(alive_enemies)

            # Атака
            perform_attack(warrior, target, round_num, True)

        round_num += 1
        if round_num > 50:
            print("\n⏰ Битва затянулась! Ничья!")
            break

        wait_for_enter()

    # Определяем победителя
    if team1_alive:
        winner_team = team1
        winner_players = [player_names[0], player_names[1]]
        winner_names = [w.name for w in winner_team if w.is_alive()]
    else:
        winner_team = team2
        winner_players = [player_names[2], player_names[3]]
        winner_names = [w.name for w in winner_team if w.is_alive()]

    print(f"\n🏆 ПОБЕДИТЕЛИ: {', '.join(winner_names)}!")
    print(f"🎉 Команда: {', '.join(winner_players)}")

    # Статистика и результаты
    print_battle_statistics(all_warriors, player_names, round_num - 1)

    # Сохраняем в историю
    battle_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "2 на 2",
        "winner": {"player": f"{winner_players[0]} и {winner_players[1]}",
                   "warrior": f"Команда: {', '.join(winner_names)}"},
        "participants": [
            {"player": player_names[0], "warrior": team1[0].name},
            {"player": player_names[1], "warrior": team1[1].name},
            {"player": player_names[2], "warrior": team2[0].name},
            {"player": player_names[3], "warrior": team2[1].name}
        ],
        "rounds": round_num - 1,
        "total_damage": sum(w.damage_dealt for w in all_warriors),
        "total_blocked": sum(w.damage_blocked for w in all_warriors)
    }
    game_manager.battle_history.add_battle(battle_data)

    # Обновляем статистику профилей
    update_profiles_statistics(game_manager, winner_players, player_names, authenticated_profiles)

    offer_save_warriors(game_manager, all_warriors)
    wait_for_enter()


def run_royal_battle(warriors, game_manager, player_names, authenticated_profiles, mode_name):
    """Общая функция для королевских битв (3 и 4 игрока)"""
    clear_screen()
    print(f"⚔️ {mode_name.upper()} - КОРОЛЕВСКАЯ БИТВА")

    # Сортируем по инициативе
    warriors.sort(key=lambda w: w.initiative, reverse=True)

    print("\n🎯 Порядок ходов:")
    for i, warrior in enumerate(warriors, 1):
        print(f"  {i}. {warrior.name} - инициатива: {warrior.initiative}")

    wait_for_enter()

    round_num = 1
    while True:
        clear_screen()
        print(f"--- Раунд {round_num} ---")

        # Показываем состояние всех игроков
        print(f"\n📊 СОСТОЯНИЕ ИГРОКОВ:")
        alive_count = 0
        for i, warrior in enumerate(warriors):
            status = "❤️" if warrior.is_alive() else "💀"
            print(f"  {status} {warrior.name}: {warrior.health}/{warrior.max_health} HP")
            if warrior.is_alive():
                alive_count += 1

        # Проверяем победу
        if alive_count <= 1:
            break

        # Ходы воинов
        for warrior in warriors:
            if not warrior.is_alive():
                continue

            # Обработка эффектов
            warrior.process_effects(round_num)
            if not warrior.is_alive():
                continue

            if warrior.is_frozen(round_num):
                print(f"❄️ {warrior.name} заморожен и пропускает ход!")
                continue

            # Выбираем живую цель (не себя)
            alive_enemies = [w for w in warriors if w != warrior and w.is_alive()]
            if not alive_enemies:
                continue

            # Выбираем случайную цель
            target = random.choice(alive_enemies)

            # Атака
            perform_attack(warrior, target, round_num, True)

        round_num += 1
        if round_num > 50:
            print("\n⏰ Битва затянулась! Ничья!")
            break

        wait_for_enter()

    # Определяем победителя
    winner = None
    for warrior in warriors:
        if warrior.is_alive():
            winner = warrior
            break

    if winner:
        winner_index = warriors.index(winner)
        winner_player = player_names[winner_index]
        print(f"\n🏆 ПОБЕДИТЕЛЬ: {winner.name} ({winner_player})!")
    else:
        print("\n🤝 Ничья! Все участники пали в бою!")

    # Статистика и результаты
    print_battle_statistics(warriors, player_names, round_num - 1)

    # Сохраняем в историю
    battle_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode_name,
        "winner": {"player": winner_player if winner else "Ничья", "warrior": winner.name if winner else "Ничья"},
        "participants": [{"player": player_names[i], "warrior": w.name} for i, w in enumerate(warriors)],
        "rounds": round_num - 1,
        "total_damage": sum(w.damage_dealt for w in warriors),
        "total_blocked": sum(w.damage_blocked for w in warriors)
    }
    game_manager.battle_history.add_battle(battle_data)

    # Обновляем статистику профилей
    if winner:
        update_profiles_statistics(game_manager, [winner_player], player_names, authenticated_profiles)

    offer_save_warriors(game_manager, warriors)
    wait_for_enter()


def run_bot_battle(warriors, game_manager, player_names, authenticated_profiles, num_bots):
    """Битва с ботами"""
    clear_screen()
    print(f"🤖 БИТВА С БОТАМИ - {len(warriors)} УЧАСТНИКОВ")

    # Сортируем по инициативе
    warriors.sort(key=lambda w: w.initiative, reverse=True)

    print("\n🎯 Порядок ходов:")
    for i, warrior in enumerate(warriors, 1):
        player_type = "Игрок" if i <= (len(warriors) - num_bots) else "Бот"
        print(f"  {i}. {warrior.name} ({player_type}) - инициатива: {warrior.initiative}")

    wait_for_enter()

    round_num = 1
    while True:
        clear_screen()
        print(f"--- Раунд {round_num} ---")

        # Показываем состояние всех участников
        print(f"\n📊 СОСТОЯНИЕ УЧАСТНИКОВ:")
        alive_count = 0
        for i, warrior in enumerate(warriors):
            player_type = "👤" if i < (len(warriors) - num_bots) else "🤖"
            status = "❤️" if warrior.is_alive() else "💀"
            print(f"  {status} {player_type} {warrior.name}: {warrior.health}/{warrior.max_health} HP")
            if warrior.is_alive():
                alive_count += 1

        # Проверяем победу
        if alive_count <= 1:
            break

        # Ходы воинов
        for i, warrior in enumerate(warriors):
            if not warrior.is_alive():
                continue

            # Обработка эффектов
            warrior.process_effects(round_num)
            if not warrior.is_alive():
                continue

            if warrior.is_frozen(round_num):
                print(f"❄️ {warrior.name} заморожен и пропускает ход!")
                continue

            # Определяем тип игрока (бот или человек)
            is_bot = i >= (len(warriors) - num_bots)

            # Выбираем живую цель (не себя)
            alive_enemies = [w for w in warriors if w != warrior and w.is_alive()]
            if not alive_enemies:
                continue

            if is_bot:
                # Боты выбирают случайную цель
                target = random.choice(alive_enemies)
            else:
                # Игрок выбирает цель
                print(f"\n🎯 Ход игрока: {warrior.name}")
                print("Доступные цели:")
                for j, enemy in enumerate(alive_enemies, 1):
                    enemy_type = "🤖" if warriors.index(enemy) >= (len(warriors) - num_bots) else "👤"
                    print(f"  {j}. {enemy_type} {enemy.name} (HP: {enemy.health}/{enemy.max_health})")

                try:
                    choice = int(input("\nВыберите цель для атаки: ")) - 1
                    if choice < 0 or choice >= len(alive_enemies):
                        print("❌ Неверный выбор, атакуем случайную цель")
                        target = random.choice(alive_enemies)
                    else:
                        target = alive_enemies[choice]
                except ValueError:
                    print("❌ Неверный ввод, атакуем случайную цель")
                    target = random.choice(alive_enemies)

            # Атака
            perform_attack(warrior, target, round_num, True)

        round_num += 1
        if round_num > 50:
            print("\n⏰ Битва затянулась! Ничья!")
            break

        wait_for_enter()

    # Определяем победителя
    winner = None
    for warrior in warriors:
        if warrior.is_alive():
            winner = warrior
            break

    if winner:
        winner_index = warriors.index(winner)
        winner_player = player_names[winner_index]
        player_type = "🤖 Бот" if winner_index >= (len(warriors) - num_bots) else "👤 Игрок"
        print(f"\n🏆 ПОБЕДИТЕЛЬ: {winner.name} ({player_type})!")
    else:
        print("\n🤝 Ничья! Все участники пали в бою!")

    # Статистика и результаты
    print_battle_statistics(warriors, player_names, round_num - 1)

    # Сохраняем в историю
    battle_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": f"Битва с ботами ({num_bots} ботов)",
        "winner": {"player": winner_player if winner else "Ничья", "warrior": winner.name if winner else "Ничья"},
        "participants": [{"player": player_names[i], "warrior": w.name} for i, w in enumerate(warriors)],
        "rounds": round_num - 1,
        "total_damage": sum(w.damage_dealt for w in warriors),
        "total_blocked": sum(w.damage_blocked for w in warriors)
    }
    game_manager.battle_history.add_battle(battle_data)

    # Обновляем статистику профилей (только для реальных игроков)
    if winner:
        winner_index = warriors.index(winner)
        if winner_index < (len(warriors) - num_bots):  # Если победил реальный игрок
            real_players = [p for i, p in enumerate(player_names) if i < (len(warriors) - num_bots)]
            real_profiles = [p for i, p in enumerate(authenticated_profiles) if i < (len(warriors) - num_bots)]
            update_profiles_statistics(game_manager, [winner_player], real_players, real_profiles)

    offer_save_warriors(game_manager, warriors)
    wait_for_enter()


def get_warriors_for_multiplayer(game_manager, num_players, mode_name):
    """Получение воинов для многопользовательской битвы с проверкой паролей"""
    clear_screen()
    print(f"\n=== {mode_name.upper()} ===")
    print("1. Создать новых персонажей")
    print("2. Загрузить из сохранения")

    choice = input("\nВыберите вариант: ")

    warriors = []
    player_names = []
    authenticated_profiles = []

    for i in range(num_players):
        clear_screen()
        print(f"\n--- Игрок {i + 1} ---")

        player_name = input("Введите имя игрока: ").strip() or f"Игрок {i + 1}"

        # Проверяем пароль для игрока
        profile = game_manager.profile_manager.verify_player_password(player_name)

        if profile:
            player_names.append(profile.username)
            authenticated_profiles.append(profile)
        else:
            player_names.append(player_name)
            authenticated_profiles.append(None)

        if choice == "1":
            warrior = create_warrior_interactive()
        elif choice == "2":
            game_manager.show_save_slots()
            slot = int(input(f"Введите слот для загрузки (1-{game_manager.total_slots}): "))
            warrior = game_manager.load_warrior(slot)
            if not warrior:
                return None, None, None
        else:
            print("❌ Неверный выбор")
            return None, None, None

        warriors.append(warrior)

    return warriors, player_names, authenticated_profiles


def start_1v1_battle(game_manager):
    if not game_manager.profile_manager.current_profile:
        print("❌ Сначала войдите в профиль")
        wait_for_enter()
        return

    clear_screen()
    print("\n=== БИТВА 1 НА 1 ===")
    print("1. Создать новых персонажей")
    print("2. Загрузить из сохранения")

    choice = input("\nВыберите вариант: ")

    # Первый игрок (текущий профиль)
    player1_name = game_manager.profile_manager.current_profile.username
    player1_profile = game_manager.profile_manager.current_profile

    # Второй игрок с проверкой пароля
    clear_screen()
    print("\n=== ВТОРОЙ ИГРОК ===")
    player2_name = input("Введите имя второго игрока: ").strip() or "Игрок 2"

    # Проверяем пароль для второго игрока
    player2_profile = game_manager.profile_manager.verify_player_password(player2_name)
    if player2_profile is None and player2_name != "Игрок 2":
        # Если профиль существует, но пароль неверный, используем имя без профиля
        player2_name = f"{player2_name} (без профиля)"

    player_names = [player1_name, player2_name]
    authenticated_profiles = [player1_profile, player2_profile]

    if choice == "1":
        clear_screen()
        print(f"\n--- Первый воин ({player1_name}) ---")
        warrior1 = create_warrior_interactive()
        clear_screen()
        print(f"\n--- Второй воин ({player2_name}) ---")
        warrior2 = create_warrior_interactive()
    elif choice == "2":
        clear_screen()
        game_manager.show_save_slots()
        slot1 = int(input(f"\nВведите слот для первого воина (1-{game_manager.total_slots}): "))
        warrior1 = game_manager.load_warrior(slot1)
        if not warrior1:
            wait_for_enter()
            return

        slot2 = int(input(f"Введите слот для второго воина (1-{game_manager.total_slots}): "))
        warrior2 = game_manager.load_warrior(slot2)
        if not warrior2:
            wait_for_enter()
            return
    else:
        print("❌ Неверный выбор")
        wait_for_enter()
        return

    # Запускаем битву 1 на 1
    run_1v1_battle(warrior1, warrior2, game_manager, player_names, authenticated_profiles)


def start_2v2_battle(game_manager):
    """Запуск битвы 2 на 2 с проверкой паролей"""
    warriors, player_names, authenticated_profiles = get_warriors_for_multiplayer(game_manager, 4, "БИТВА 2 НА 2")
    if not warriors:
        return

    # Разделяем на команды
    team1 = warriors[:2]
    team2 = warriors[2:]
    team1_names = player_names[:2]
    team2_names = player_names[2:]
    team1_profiles = authenticated_profiles[:2]
    team2_profiles = authenticated_profiles[2:]

    all_player_names = team1_names + team2_names
    all_authenticated_profiles = team1_profiles + team2_profiles

    run_2v2_battle(team1, team2, game_manager, all_player_names, all_authenticated_profiles)


def start_3player_battle(game_manager):
    """Запуск битвы 3 игрока с проверкой паролей"""
    warriors, player_names, authenticated_profiles = get_warriors_for_multiplayer(game_manager, 3, "БИТВА 3 ИГРОКА")
    if not warriors:
        return

    run_royal_battle(warriors, game_manager, player_names, authenticated_profiles, "3 игрока")


def start_4player_battle(game_manager):
    """Запуск битвы 4 игрока с проверкой паролей"""
    warriors, player_names, authenticated_profiles = get_warriors_for_multiplayer(game_manager, 4, "БИТВА 4 ИГРОКА")
    if not warriors:
        return

    run_royal_battle(warriors, game_manager, player_names, authenticated_profiles, "4 игрока")


def start_bot_battle(game_manager):
    """Запуск битвы с ботами с проверкой паролей"""
    clear_screen()
    print("🤖 БИТВА С БОТАМИ")
    print("=" * 30)

    # Выбор количества ботов
    try:
        num_bots = int(input("Введите количество ботов (1-5): "))
        if num_bots < 1 or num_bots > 5:
            print("❌ Неверное количество ботов. Допустимо: 1-5")
            wait_for_enter()
            return
    except ValueError:
        print("❌ Введите число")
        wait_for_enter()
        return

    # Выбор количества игроков
    try:
        num_players = int(input("Введите количество игроков (1-3): "))
        if num_players < 1 or num_players > 3:
            print("❌ Неверное количество игроков. Допустимо: 1-3")
            wait_for_enter()
            return
    except ValueError:
        print("❌ Введите число")
        wait_for_enter()
        return

    total_participants = num_players + num_bots
    if total_participants < 2:
        print("❌ Должен быть хотя бы 1 игрок и 1 бот")
        wait_for_enter()
        return

    warriors = []
    player_names = []
    authenticated_profiles = []

    # Создание персонажей для игроков с проверкой паролей
    for i in range(num_players):
        clear_screen()
        print(f"\n--- Игрок {i + 1} ---")

        player_name = input("Введите имя игрока: ").strip() or f"Игрок {i + 1}"

        # Проверяем пароль для игрока
        profile = game_manager.profile_manager.verify_player_password(player_name)

        if profile:
            player_names.append(profile.username)
            authenticated_profiles.append(profile)
        else:
            player_names.append(player_name)
            authenticated_profiles.append(None)

        print("1. Создать нового персонажа")
        print("2. Загрузить из сохранения")
        choice = input("Выберите вариант: ")

        if choice == "1":
            warrior = create_warrior_interactive()
        elif choice == "2":
            game_manager.show_save_slots()
            slot = int(input(f"Введите слот для загрузки (1-{game_manager.total_slots}): "))
            warrior = game_manager.load_warrior(slot)
            if not warrior:
                return
        else:
            print("❌ Неверный выбор")
            return

        warriors.append(warrior)

    # Создание ботов
    for i in range(num_bots):
        bot_warrior = generate_bot_warrior(i + 1)
        warriors.append(bot_warrior)
        player_names.append(f"Бот {i + 1}")
        authenticated_profiles.append(None)

    # Запуск битвы с ботами
    run_bot_battle(warriors, game_manager, player_names, authenticated_profiles, num_bots)


def battle_modes_menu(game_manager):
    """Меню режимов сражений"""
    while True:
        clear_screen()
        print("🎯 РЕЖИМЫ СРАЖЕНИЙ")
        print("=" * 50)
        print(f"\n1. Битва 1 на 1")
        print(f"2. Битва 2 на 2 (командная)")
        print(f"3. Битва 3 игрока (королевская битва)")
        print(f"4. Битва 4 игрока (каждый за себя)")
        print(f"5. Битва с ботами")
        print(f"6. Назад в главное меню")

        choice = input("\nВыберите режим: ")

        if choice == "1":
            start_1v1_battle(game_manager)
        elif choice == "2":
            start_2v2_battle(game_manager)
        elif choice == "3":
            start_3player_battle(game_manager)
        elif choice == "4":
            start_4player_battle(game_manager)
        elif choice == "5":
            start_bot_battle(game_manager)
        elif choice == "6":
            break
        else:
            print("❌ Неверный выбор")
            wait_for_enter()


def create_and_save_warrior(game_manager):
    if not game_manager.profile_manager.current_profile or not game_manager.profile_manager.current_profile.is_developer:
        print("❌ Только разработчики могут создавать персонажей")
        wait_for_enter()
        return

    clear_screen()
    print("\n=== СОЗДАНИЕ И СОХРАНЕНИЕ ПЕРСОНАЖА ===")

    game_manager.show_save_slots()
    slot = int(input(f"\nВведите слот для сохранения (1-{game_manager.total_slots}): "))

    if slot < 1 or slot > game_manager.total_slots:
        print(f"❌ Неверный слот. Допустимые значения: 1-{game_manager.total_slots}")
        wait_for_enter()
        return

    warrior = create_warrior_interactive()
    game_manager.save_warrior(warrior, slot)
    wait_for_enter()


def show_save_slots_menu(game_manager):
    clear_screen()
    print("\n=== СЛОТЫ СОХРАНЕНИЯ ===")
    game_manager.show_save_slots()
    wait_for_enter()


def edit_warrior_menu(game_manager):
    clear_screen()
    print("\n=== РЕДАКТИРОВАНИЕ ПЕРСОНАЖА ===")

    game_manager.show_save_slots()
    slot = int(input(f"\nВведите слот для редактирования (1-{game_manager.total_slots}): "))

    if slot < 1 or slot > game_manager.total_slots:
        print(f"❌ Неверный слот. Допустимые значения: 1-{game_manager.total_slots}")
        wait_for_enter()
        return

    game_manager.edit_warrior(slot)


def delete_warrior_menu(game_manager):
    clear_screen()
    print("\n=== УДАЛЕНИЕ ПЕРСОНАЖА ===")

    game_manager.show_save_slots()
    slot = int(input(f"\nВведите слот для удаления (1-{game_manager.total_slots}): "))

    if slot < 1 or slot > game_manager.total_slots:
        print(f"❌ Неверный слот. Допустимые значения: 1-{game_manager.total_slots}")
        wait_for_enter()
        return

    game_manager.delete_warrior(slot)


def profile_menu(game_manager):
    while True:
        clear_screen()
        print("👤 УПРАВЛЕНИЕ ПРОФИЛЕМ")
        print("=" * 30)

        if game_manager.profile_manager.current_profile:
            print(f"Текущий профиль: {game_manager.profile_manager.current_profile.username}")
            if game_manager.profile_manager.current_profile.is_developer:
                print("🔧 Режим разработчика")
            print(f"🏆 Побед: {game_manager.profile_manager.current_profile.wins}")
            print(f"💔 Поражений: {game_manager.profile_manager.current_profile.losses}")
            print(f"⭐ Рейтинг: {game_manager.profile_manager.current_profile.rating}")
        else:
            print("❌ Профиль не выбран")

        print(f"\n1. Создать профиль")
        print(f"2. Войти в профиль")
        print(f"3. Выйти из профиля")
        print(f"4. Назад")

        choice = input("\nВыберите действие: ")

        if choice == "1":
            new_profile = game_manager.profile_manager.create_profile()
            if new_profile:
                game_manager.profile_manager.current_profile = new_profile
        elif choice == "2":
            game_manager.profile_manager.login()
        elif choice == "3":
            game_manager.profile_manager.logout()
        elif choice == "4":
            break
        else:
            print("❌ Неверный выбор")
            wait_for_enter()


def main():
    game_manager = GameManager()
    game_manager.create_default_warriors()

    while True:
        clear_screen()
        print("🎮 МИНИ-ИГРА 'БИТВА' 🎮")
        print("=" * 50)

        if game_manager.profile_manager.current_profile:
            print(f"👤 Текущий профиль: {game_manager.profile_manager.current_profile.username}")
            if game_manager.profile_manager.current_profile.is_developer:
                print("🔧 Режим разработчика")
            print(f"🏆 Побед: {game_manager.profile_manager.current_profile.wins} | "
                  f"Поражений: {game_manager.profile_manager.current_profile.losses}")
        else:
            print("❌ Профиль не выбран")

        print(f"\n1. Профиль")
        print(f"2. Режимы сражений")
        print(f"3. Создать и сохранить персонажа")
        print(f"4. Показать слоты сохранения")
        print(f"5. Редактировать персонажа")
        print(f"6. Удалить персонажа")
        print(f"7. История битв")
        print(f"8. Таблица лидеров")
        print(f"9. Обучение")
        print(f"0. Выйти")

        choice = input("\nВыберите действие: ")

        if choice == "1":
            profile_menu(game_manager)
        elif choice == "2":
            if game_manager.profile_manager.current_profile:
                battle_modes_menu(game_manager)
            else:
                print("❌ Сначала войдите в профиль")
                wait_for_enter()
        elif choice == "3":
            create_and_save_warrior(game_manager)
        elif choice == "4":
            show_save_slots_menu(game_manager)
        elif choice == "5":
            edit_warrior_menu(game_manager)
        elif choice == "6":
            delete_warrior_menu(game_manager)
        elif choice == "7":
            game_manager.battle_history.show_history()
        elif choice == "8":
            game_manager.leaderboard.show_leaderboard()
        elif choice == "9":
            show_tutorial()
        elif choice == "0":
            clear_screen()
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")
            wait_for_enter()


if __name__ == "__main__":
    main()