import argparse
import logging
from json import load
from os import makedirs
from os.path import exists as file_exists, join
from typing import List
from requests import get as rget

def get_scryfall_data() -> None:
  url = 'https://api.scryfall.com/bulk-data'
  reqs = rget(url, timeout=1).json()['data'][0]['download_uri']
  with open(join('config', 'cardlist.json'), 'wb') as file:
    file.write(rget(reqs).content)

def in_format(card: dict, card_format: str) -> bool:
  if card['layout'] == 'transform':
    return False
  return card['legalities'][card_format] != 'not_legal'

def remove_unneeded_attributes(cardpool: List[dict], args) -> None:
  with open(join('config', 'unneeded_attributes.json')) as file:
    unneeded_attributes = load(file)
  with open(join('config', 'unneeded_attributes_low.json')) as file:
    potentially_unneeded_attributes = load(file)

  for card in cardpool:
    for attribute in unneeded_attributes:
      if attribute in card:
        del card[attribute]
    
    if args.granularity == 'low':
      for attribute in potentially_unneeded_attributes:
        if attribute in card:
          del card[attribute]
  
def generate_training_data(args, filename: str = 'cardlist.json') -> None:
  with open(join('config', filename), encoding="utf8") as file:
    cards = load(file)

  makedirs('./output', exist_ok=True)
  
  if args.format_filter:
    cardpool = [card for card in cards if in_format(card, args.format_filter) and card['layout'] != 'transform' and '//' not in card['name']]

  elif args.file_filter:  
    with open(join('output', args.file_filter)) as file:
      file_filter = file.readlines()
      file_filter = [card.strip() for card in file_filter]
    cardpool = [card for card in cards if card['name'] in file_filter and card['layout'] != 'transform' and '//' not in card['name']]

  remove_unneeded_attributes(cardpool, args)
  
  with open(join('output', 'training_data.jsonl'), 'w', encoding="utf8") as file:
    for card in cardpool:
      card_data = ""
      for attribute, value in card.items():
        if attribute != 'cmc' and attribute != 'colors':
          card_data += attribute + ": " + str(value).replace("\"", "\'") + "\n"
      card_data = card_data.replace("\n", "\\n")
      if args.granularity == 'low':
        file.write(f'{{"prompt":"{card["type_line"].split()[0]} ->","completion":" {card_data}ꙮ"}}\n')
      else:
        file.write(f'{{"prompt":"CMC {int(card["cmc"])} {card["colors"]} '
                   f'{card["type_line"].split()[0]} ->","completion":" {card_data}ꙮ"}}\n')
    print(f'# created: {len(cardpool)}')

def parse_args():
  parser = argparse.ArgumentParser(
    description="a script to prepare a dataset for training. only one filter flag is considered.")
  parser.add_argument("--file_filter", type=str, help='provide a filename for filter', default='cards_in_legacy_mainboard_all.jsonl')
  parser.add_argument("--format_filter", type=str)
  parser.add_argument("--granularity", type=str, choices=['high', 'low'], default='low',
                      help='set to high if you want to specify color and cmc')
  args = parser.parse_args()
  print(args)
  return args

def main() -> None:
  makedirs('./logs', exist_ok=True)
  logging.basicConfig(filename=join('logs', 'dataset.log'), encoding='utf-8', level=logging.DEBUG)

  arguments = parse_args()  

  if not file_exists(join('config', 'cardlist.json')):
    get_scryfall_data()

  if file_exists(join('config', 'cardlist.json')):
    generate_training_data(arguments)

if __name__ == '__main__':
  main()